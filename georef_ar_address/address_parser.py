"""Módulo address_parser.py de georef-ar-address

Contiene clases y funciones utilizadas para extraer components de direcciones
de calles en Argentina. La extracción opera exclusivamente con texto, y nunca
consulta recursos externos (todo el procesamiento se hace localmente).

Para ver información sobre el diseño de address_parser.py, ver el archivo
docs/design.md.

"""

import re
import os
import nltk
from .address_data import AddressData

_GRAMMARS_DIR = os.path.join(os.path.dirname(__file__), 'grammars')
_GRAMMAR_PATH = os.path.join(_GRAMMARS_DIR, 'address-ar.cfg')
_START_PRODUCTION = 'address'

_SEPARATION_REGEXP = r'([^\W\d]{2,}\.?)(\d)'
"""str: Expresión regular utilizada en la etapa de normalización para separar
letras seguidas de números.
"""

_NORMALIZATION_REGEXPS = [
    # Remover aclaraciones entre paréntesis
    r'\((ex|antes|frente|mano|(al\s)?lado).+?\)',
    # Remover información de localidad
    r'([vb][°ºª]|barrio\s|bo\.\s).*',
    # Remover aclaraciones de orientación ("(N)" == "norte")
    r'\([sneo]\)',
    # Remover comas utilizadas para separar texto
    r',(\s|$)|\s,',
    # Algunos caracteres pueden ser removidos sin modificar el significado del
    # texto que los rodea
    r'[()"|]',
    # Remover guiones al final del texto
    r'-+$',
    # Remover guiones con espacios
    r'\s-+|-+\s',
    # Remover palabra 'al' antes de un número
    r'\sal\s+(?=\d)'
]
"""list: Lista de expresiones regulares utilizadas en la etapa de
normalización. Cada expresión representa partes del valor de entrada de
AddressParser.parse() que pueden ser eliminados sin perder información
importante.
"""

_TOKEN_TYPES = [
    ('AND_WORD', r'y\s(?=\D)|e\s(?=h?[iy])'),
    ('AND_NUM', r'y\s(?=\d)'),
    ('OF', r'de\s'),
    ('FLOOR', r'piso(\s|$)'),
    ('DOOR_TYPE', r'(d(e?p)?to\.?|departamento|oficina|of\.)\s'),
    ('GROUNDL', r'(p\.?b\.?|planta\sbaja)(\s|$)'),
    ('ISCT_SEP', r'esquina|esq\.|esq\s|esq/'),
    ('BTWN_SEP', r'e/(calles)?|entre\scalles'),
    ('BETWEEN', r'entre\s'),
    ('KM', r'kil[oó]metro|km\.?'),
    ('MISSING_NAME', r's/nombre'),
    ('MISSING_NUM', r'(sin\s|s/)(n[uú]mero|n(ro\.?|[°º]))'),
    ('S_N', r's[/-]n|s\s?n(\s|$)'),
    ('STREET_TYPE_S', r'(avda|av|bv|diag|pje)[\s.]'),
    ('STREET_TYPE_L', r'calle\s|avenida|bo?ulevard?|diagonal|pasaje'),
    ('ROUTE', r'ruta|(rta|rn|rp)[\s.]'),
    ('NUM_LABEL_S', r'n\s?[°ºª*]|#|n(?=\d)'),
    ('NUM_LABEL_L', r'nro[\s.]|n[uú]mero'),
    ('DECIMAL', r'\d+[.,]\d+'),
    ('NUM_RANGE', r'\d+[/-]\d+([/-]\d+)*'),
    ('ORDINAL', r'\d+(era?|nd[oa]|[nmtvr][oa])(\s|$|\.)'),
    ('NUM', r'\d+((\s|$)|[°º])'),
    ('N', r'n\s'),
    ('LETTER', r'[^\d\W](\s|$|\.)'),
    ('NUMS_LETTER', r'[\d]+[^\d\W](\s|$)'),
    ('WORD', r'[^\s]+'),
    ('WS', r'\s')
]
"""list: Expresiones regulares utilizadas para crear cada tipo de token en la
etapa de tokenización.
"""


class InvalidGrammarException(Exception):
    """Excepción lanzada cuando se intenta cargar una gramática con uno o más
    problemas de estructura.

    """

    pass


def _with_labels(labels):
    """Crea un predicado para nltk.Tree que devuelve True si su etiqueta está
    dentro de un conjunto de valores.

    Args:
        list: Lista de valores.

    Returns:
        function: función que retorna True si el llamado a 'label' de su
            argumento retorna un objeto que pertenece a un conjunto de valores.

    """
    return lambda t: t.label() in set(labels)


def _load_grammar(grammar_path):
    """Lee una gramática libre de contexto almacenada en un archivo .cfg y
    la retorna luego de realizar algunas validaciones.

    Args:
        grammar_path (str): Ruta a un archivo .cfg conteniendo una gramática
            libre de contexto en el formato utilizado por NLTK.

    Raises:
        InvalidGrammarException: en caso de que la gramática no sea válida.

    Returns:
        nltk.CFG: Gramática libre de contexto leída del archivo.

    """
    grammar = nltk.data.load('file:{}'.format(grammar_path))

    if grammar.start().symbol() != _START_PRODUCTION:
        raise InvalidGrammarException('Start rule must be "{}"'.format(
            _START_PRODUCTION))

    if not grammar.is_nonempty():
        raise InvalidGrammarException('Empty productions are not allowed')

    nonterminals = set()
    terminals = {token_name for token_name, _ in _TOKEN_TYPES}

    for production in grammar.productions():
        nonterminals.add(production.lhs().symbol())

    for production in grammar.productions():
        for element in production.rhs():
            symbol = str(element)

            if nltk.grammar.is_nonterminal(element):
                if symbol not in nonterminals:
                    raise InvalidGrammarException(
                        'Invalid nonterminal: {}'.format(symbol))
            elif symbol not in terminals:
                raise InvalidGrammarException(
                    'Invalid terminal: {}'.format(symbol))

    return grammar


class TreeVisitor:
    """La clase TreeVisitor es utilizada para extraer información útil de
    instancias de nltk.Tree.

    Attributes:
        self._tree: Instancia de nltk.Tree asociada al TreeVisitor. El árbol
            nunca se modifica en ninguno de los métodos internos utilizados.
        self._rank: Rango (puntaje) del árbol de parseo contenido en
            self._tree.

    """

    __slots__ = ['_tree', '_rank', '_components_leaves_indices']

    def __init__(self, tree):
        """Inicializa un objeto de tipo TreeVisitor.

        Args:
            tree (nltk.Tree): Árbol de parseo.

        """
        self._tree = tree
        self._rank = None
        self._components_leaves_indices = None

    def _get_components_leaves_indices(self):
        """Retorna listas de índices de hojas por cada componente de dirección
        en el árbol '_tree'. Es decir, por cada subarbol de interés de '_tree'
        (por ejemplo, 'floor'), recorre todas sus hojas, y toma nota de sus
        índices dentro de el arbol completo.

        Por ejemplo, teniendo el siguiente árbol de parseo (simplificado) para
        los tokens [(SARMIENTO, WORD), (1400, NUM), (2, NUM), (C, LETTER)], de
        la dirección "Sarmiento 1400 2 C":

                        address
                           |
                         simple
                           |
                          /|\
                         / | \
           --------------  |  ------------------
           |               |                   |
         street     door_number_value        floor
           |               |                   /\
           |               |                  /  \
          WORD            NUM               NUM  LETTER

        Los índices de hojas de cada componentes serían:
        - street: [0]
        - door_num_value: [1]
        - floor: [2, 3]

        La cantidad total de hojas siempre es igual a la cantidad de tokens, ya
        que un árbol de parseo solo es devuelto si cubre la totalidad de los
        tokens especificados.

        Los índices luego son utilizados para acceder a la lista de tokens, y
        tomar los valores de los mismos. En el ejemplo anterior, los índices
        [2, 3] resultarían en los valores '2' y 'C', el piso de la dirección.
        Notar que para la componente 'street' se arma (potencialmente) más de
        una lista, ya que puede haber más de una calle en una dirección.

        Returns:
            dict: Diccionario con listas de índices de hojas de cada componente
                de la dirección.

        """
        # Operar sobre una copia de _tree para no modificar el árbol original.
        # La copia se hace una sola vez y no es costosa en comparación a las
        # otras partes del proceso de parseo.
        tree = self._tree.copy(deep=True)

        for i, tree_pos in enumerate(tree.treepositions('leaves')):
            # Modificar nuestro árbol 'tree' para que cada hoja contenga su
            # propio índice dentro del árbol completo, comenzando desde la
            # izquierda (anteriormente, cada hoja contenía el tipo de su token
            # correspondiente en la lista de tokens).
            tree[tree_pos] = i

        components_leaves_indices = {
            'street': [],
            'door_number_value': None,
            'door_number_unit': None,
            'floor': None
        }

        condition = _with_labels(components_leaves_indices.keys())

        # Recorrer cada subarbol de interés
        for subtree in tree.subtrees(condition):
            label = subtree.label()

            # Tomar la lista de índices de las hojas
            leaves_indices = subtree.leaves()

            # Almacenar la lista en el diccionario, dependiendo de bajo qué
            # subarbol estemos
            if label == 'street':
                components_leaves_indices['street'].append(leaves_indices)
            elif label == 'door_number_value':
                components_leaves_indices['door_number_value'] = leaves_indices
            elif label == 'door_number_unit':
                components_leaves_indices['door_number_unit'] = leaves_indices
            elif label == 'floor':
                components_leaves_indices['floor'] = leaves_indices

        return components_leaves_indices

    def _select_token_values(self, tokens, indices):
        """Dada una lista de tokens, selecciona un subconjunto y retorna sus
        valores concatenados.

        Args:
            tokens (list): Lista de tokens. Cada token es una tipla de tipo
                (str, str), donde el primer string es una parte textual de una
                dirección, y el segundo es un tipo de token.
            indices (list): Lista de índices de tokens a seleccionar, en el
                orden especificado.

        Returns:
            str: Valor de los tokens concatenados con espacios.

        """
        return ' '.join([tokens[i][0] for i in indices])

    def extract_data(self, tokens):
        """Dada una lista de tokens, utiliza el árbol de parseo interno para
        determinar a qué componente de dirección pertenece cada token. Luego,
        se retornan las componentes de dirección construidas a partir de esa
        información y los valores contenidos dentro de los tokens.

        Args:
            tokens (list): Lista de tokens. Cada token es una tipla de tipo
                (str, str), donde el primer string es una parte textual de una
                dirección, y el segundo es un tipo de token.

        Returns:
            tuple: Tupla de tipo (list, str, str, str), donde cada valor es la
                lista de nombres de calles encontrados, la altura (valor), la
                altura (unidad) y el piso, respectivamente.

        """
        if not self._components_leaves_indices:
            # Calcular los índices de las hojas de los árboles de componentes
            # una sola vez y almacenarlos.
            self._components_leaves_indices = \
                self._get_components_leaves_indices()

        # Utilizar _components_leaves_indices para seleccionar los tokens
        # indicados y construir los valores de las componentes de la dirección.
        street_names = [
            self._select_token_values(tokens, indices)
            for indices in self._components_leaves_indices['street']
        ]

        door_num_value = None
        door_num_unit = None
        floor = None

        if self._components_leaves_indices['door_number_value']:
            door_num_value = self._select_token_values(
                tokens, self._components_leaves_indices['door_number_value'])

        if self._components_leaves_indices['door_number_unit']:
            door_num_unit = self._select_token_values(
                tokens, self._components_leaves_indices['door_number_unit'])

        if self._components_leaves_indices['floor']:
            floor = self._select_token_values(
                tokens, self._components_leaves_indices['floor'])

        return street_names, door_num_value, door_num_unit, floor

    def _get_rank(self):
        """Calcula el rango (puntaje) de 'self._tree'. El rango es utilizado
        en la etapa de desambiguación, para elegir el mejor árbol entre varios.

        El rango está compuesto de tres valores:
        - Cantidad de calles sin nombres encontradas en 'self._tree'
        - La presencia o no de una altura en 'self._tree' (1 o 0)
        - Rango del tipo de dirección encontrado en 'self._tree'

        El significado de cada valor se explica más en detalle en el archivo
        docs/design.md.

        Returns:
            tuple: Tupla de tipo (int, int, int). Los valores más altos son
                mejores.

        """
        has_door_number = False
        unnamed_streets = 0

        condition = _with_labels(['street_no_num', 'street_with_num'])

        # Recorrer cada subarbol de interés
        for subtree in self._tree.subtrees(condition):
            if subtree.label() == 'street_with_num':
                has_door_number = True

            if subtree[0][0].label() == 'unnamed_street':
                unnamed_streets += 1

        # La presencia o no de una altura afecta el rango del tipo de la
        # dirección
        if has_door_number:
            ranks = ['intersection', 'simple', 'between']
        else:
            ranks = ['simple', 'intersection', 'between']

        rank = ranks.index(self.address_type)

        return (unnamed_streets, int(has_door_number), rank)

    @property
    def rank(self):
        # Cachear el rango para evitar calcularlo varias veces. Como el valor
        # de self._tree nunca se modifica, esto no puede traer problemas.
        if not self._rank:
            self._rank = self._get_rank()

        return self._rank

    @property
    def address_type(self):
        return self._tree.label()


class AddressParser:
    """Clase utilizada para extraer componentes de direcciones argentinas.

    El proceso de extracción consiste de cinco etapas, explicadas en detalle en
    el archivo docs/design.md.

    Se puede especificar opcionalmente un cache a utilizar, para evitar parsear
    una misma lista de tipos de tokens más de una vez. Esto puede suceder
    cuando dos direcciones generan una misma lista de tipos de tokens, como
    por ejemplo:

    'Tucumán 1000' ---> [WORD, INT]
    'Córdoba 2000' ---> [WORD, INT]

    Notar que si no se especifica un cache, la clase AddressParser tiene un
    estado interno completamente inmutable. Por el otro lado, el uso de cache
    aumenta considerablemente la performance del proceso de extracción.

    Attributes:
        _parser (nltk.EarleyChartParser): Instancia de parser Earley utilizado
            en la etapa de parseo.
        _token_regexp (_sre.SRE_Pattern): Expresión regular utilizada en la
            generación de tokens.
        _separation_regexp (_sre.SRE_Pattern): Expresión regular utilizada en
            la etapa de normalización (separación de letras y números).
        _normalization_regexp (_sre.SRE_Pattern): Expresión regular utilizada
            en la etapa de normalización.
        _cache (dict): Objeto dict-like utilizado para cachear árboles de
            parseo. Puede ser 'None' (no utilizar cache).

    """

    def __init__(self, cache=None):
        """Inicializa un objecto de tipo AddressParser.

        Args:
            cache (dict): Ver atributo 'self._cache'.

        """
        self._parser = nltk.EarleyChartParser(_load_grammar(_GRAMMAR_PATH))

        self._token_regexp = re.compile(
            '|'.join('(?P<{}>{})'.format(*tt) for tt in _TOKEN_TYPES),
            re.IGNORECASE)

        self._separation_regexp = re.compile(_SEPARATION_REGEXP, re.IGNORECASE)

        self._normalization_regexp = re.compile(
            '|'.join(_NORMALIZATION_REGEXPS),
            re.IGNORECASE
        )

        self._cache = cache

    def _tokenize_address(self, address):
        """Genera una lista de tokens a partir de una potencial dirección.

        Args:
            address (str): Dirección normalizada.

        Raises:
            InvalidTokenException: en caso de encontrar un token de tipo
                UNKNOWN.

        Returns:
            list: Lista de tokens. Cada token es de tipo tuple (str, str),
                donde el primer string es una parte textual de la dirección, y
                el segundo es el tipo del token.

        """
        tokens = []
        for mo in self._token_regexp.finditer(address):
            kind = mo.lastgroup
            value = mo.group().strip()

            if kind != 'WS':
                tokens.append((value, kind))

        return tokens

    def _normalize_address(self, address):
        """Normaliza una dirección, removiendo partes del texto que no son de
        utilidad.

        Args:
            address (str): Dirección a normalizar.

        Returns:
            str: Dirección normalizada.

        """
        # Reemplazar partes no deseadas por espacios
        normalized = self._normalization_regexp.sub(' ', address.strip())

        # Separar dos o más letras pegadas a números (en ese orden):
        # Sí: 'hola123' -> 'hola 123'
        # Sí: 'ruta nac.3' -> 'ruta nac. 3'
        # No: '1ro de Mayo' -> '1ro de Mayo'
        # No: 'Lote 14 M2' -> 'Lote 14 M2'
        normalized = self._separation_regexp.sub(r'\1 \2', normalized)

        # Normalizar espacios (también remueve trailing/leading whitespace)
        return ' '.join(normalized.split())

    def _disambiguate_trees(self, visitors):
        """Dada una lista de árboles de parseo, toma el mejor utilizando el
        rango de cada uno como criterio de decisión. Para ver más detalles de
        la etapa de desambiguación, ver el archivo docs/design.md.

        Args:
            visitors (list): Lista de TreeVisitor.

        Returns:
            TreeVisitor, NoneType: Se retorna el mejor TreeVisitor si se pudo
                encontrar uno inequívocamente, o None si no fue posible.

        """
        if len(visitors) == 1:
            return visitors[0]

        visitors.sort(key=lambda v: v.rank, reverse=True)

        # La lista de árboles ahora está ordenada de mejor a peor. Comparar
        # el rango (puntaje) del primer elemento con el del segundo: si son
        # iguales, entonces hay dos o más árboles con el mismo rango
        # maximal. Esto quiere decir que todos estos árboles son una
        # solución viable, pero no es posible distinguir cuál de ellos es
        # el más adecuado. Si sucede esto, devolver None.
        if visitors[0].rank == visitors[1].rank:
            return None

        return visitors[0]

    def _tokens_parse_tree(self, token_types):
        """Dada una lista de *tipos* de tokens, retorna el mejor árbol de
        parseo.

        Args:
            token_types (list): Lista de tipos de tokens.

        Returns:
            TreeVisitor, NoneType: El mejor TreeVisitor encontrado, o None si
                no existe.

        """
        visitors = [
            # tree[0] toma el subárbol debajo de la producción 'address'
            TreeVisitor(tree[0])
            for tree in
            self._parser.parse(token_types)
        ]

        return self._disambiguate_trees(visitors) if visitors else None

    def _parse_token_types(self, token_types):
        """El método '_parse_token_types' es simplemente un wrapper de
        '_tokens_parse_tree' que utiliza 'self._cache' para evitar operaciones
        innecesarias (si no es 'None'). Ver el archivo docs/design.md para más
        detalles de esta mejora de rendimiento.

        Args:
            token_types (list): Lista de tipos de tokens.

        Returns:
            TreeVisitor, NoneType: El mejor TreeVisitor encontrado, o None si
                no existe.

        """
        if self._cache is not None:
            tokens_hash = hash(tuple(token_types))

            if tokens_hash in self._cache:
                return self._cache[tokens_hash]

            tree = self._tokens_parse_tree(token_types)
            self._cache[tokens_hash] = tree
            return tree

        return self._tokens_parse_tree(token_types)

    def parse(self, address):
        """Punto de entrada de la clase AddressParser. Toma una dirección como
        string e intenta extraer sus componentes, utilizando el proceso
        detallado en el archivo docs/design.md.

        Args:
            address (str): Dirección sobre la cual realizar la extracción de
                componentes.

        Returns:
            AddressData, NoneType: Si se pudieron extraer las componente
                con éxito, se retorna una instancia de 'AddressData' con los
                valores apropiados. En caso contrario se retorna 'None'.

        """
        # 1) Normalizar
        processed = self._normalize_address(address)

        if not processed:
            return None

        # 2) Tokenizar
        tokens = self._tokenize_address(processed)

        # 3) Parsear y 4) Desambiguar
        visitor = self._parse_token_types([
            t_type for _, t_type in tokens
        ])

        if not visitor:
            return None

        # 5) Ensamblar
        street_names, door_number_value, door_number_unit, floor = \
            visitor.extract_data(tokens)

        return AddressData(visitor.address_type, street_names,
                           (door_number_value, door_number_unit), floor)
