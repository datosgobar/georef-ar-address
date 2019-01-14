"""Módulo address_parser.py

Contiene clases y funciones utilizadas para extraer components de direcciones
de calles en Argentina. La extracción opera exclusivamente con texto, y nunca
consulta recursos externos (todo el procesamiento se hace localmente).

Para ver información sobre el diseño de address_parser.py, ver el archivo
docs/design.md.

"""

import re
import os
import copy
import nltk

GRAMMARS_DIR = os.path.join(os.path.dirname(__file__), 'grammars')
GRAMMAR_PATH = os.path.join(GRAMMARS_DIR, 'address-ar.cfg')
START_PRODUCTION = 'address'

ADDRESS_DATA_TEMPLATE = {
    'street_names': [],
    'door_number': {
        'value': None,
        'unit': None
    },
    'floor': None,
    'type': None
}
"""dict: Estructura de respuesta para el método AddressParser.parse().
Los valores internos son modificados luego de finalizar la extracción de
componentes del valor de entrada.
"""

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
    ('S_N', r's[/-]n|sn(\s|$)'),
    ('STREET_TYPE_S', r'(avda|av|bv|diag)[\s.]'),
    ('STREET_TYPE_L', r'calle\s|avenida|bo?ulevard?|diagonal'),
    ('ROUTE', r'ruta|(rta|rn|rp)[\s.]'),
    ('NUM_LABEL_S', r'n\s?[°ºª*]|#|n(?=\d)'),
    ('NUM_LABEL_L', r'nro[\s.]|n[uú]mero'),
    ('DECIMAL', r'\d+[.,]\d+'),
    ('NUM_RANGE', r'\d+[/-]\d+([/-]\d+)*'),
    ('ORDINAL', r'\d+(era?|nd[oa]|[nmtvr][oa])(\s|$|\.)'),
    ('NUM', r'\d+((\s|$)|[°º])'),
    ('N', r'n\s'),
    ('LETTER', r'[^\d\W](\s|$|\.)'),
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


def with_labels(labels):
    """Crea un predicado para nltk.Tree que devuelve True si su etiqueta está
    dentro de un conjunto de valores.

    Args:
        list: Lista de valores.

    Returns:
        function: función que retorna True si el llamado a 'label' de su
            argumento retorna un objeto que pertenece a un conjunto de valores.

    """
    return lambda t: t.label() in set(labels)


def load_grammar(grammar_path):
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

    if grammar.start().symbol() != START_PRODUCTION:
        raise InvalidGrammarException('Start rule must be "{}"'.format(
            START_PRODUCTION))

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

    __slots__ = ['_tree', '_rank']

    def __init__(self, tree):
        """Inicializa un objeto de tipo TreeVisitor.

        Args:
            tree (nltk.Tree): Árbol de parseo.

        """
        self._tree = tree
        self._rank = None

    def extract_data(self, tokens):
        """Dada una lista de tokens, utiliza el atributo 'self._tree' para
        determinar a qué componente de una dirección pertenece cada token.

        Para lograr esto, se recorre el árbol buscando nodos de interés
        (street, door_number_value, etc.) y por cada subarbol se extraen sus
        hojas. La secuencia de hojas se concatena para formar el valor final
        representado por ese subarbol.

        Args:
            tokens (list): Lista de tokens. Cada token es una tipla de tipo
                (str, str), donde el primer string es una parte textual de una
                dirección, y el segundo es un tipo de token.

        Returns:
            tuple: Tupla de tipo (list, str, str, str), donde cada valor es la
                lista de nombres de calles encontrados, la altura (valor), la
                altura (unidad) y el piso, respectivamente.

        """
        tree = self._tree.copy(deep=True)

        # El árbol self._tree contiene los *tipos* de los tokens en sus hojas.
        # Cada token en la lista de tokens tiene una hoja correspondiente en el
        # árbol, en forma secuencial. Es decir, el token número N corresponde a
        # la hoja número N del árbol, comenzando desde la izquierda.
        # Para poder inspeccionar el árbol de forma fácil, se necesita que cada
        # hoja del árbol contenga el *valor* de su token correspondiente, no su
        # tipo. Para lograr esto, se crea una copia de self._tree, y por cada
        # token se reemplaza su hoja correspondiente con el valor del mismo.
        # Es importante no modificar self._tree ya que potencialmente podría
        # ser utilizado para extraer información de otra lista de tokens.
        for i, tree_pos in enumerate(tree.treepositions('leaves')):
            tree[tree_pos] = tokens[i][0]

        street_names = []
        door_number_value = None
        door_number_unit = None
        floor = None
        condition = with_labels([
            'street',
            'door_number_value',
            'door_number_unit',
            'floor'
        ])

        # Recorrer cada subarbol de interés
        for subtree in tree.subtrees(condition):
            label = subtree.label()

            # Concatenar las hojas del subarbol, construyendo así el texto que
            # yace 'debajo' del subarbol.
            subtree_text = ' '.join(subtree.leaves())

            if label == 'street':
                street_names.append(subtree_text)
            elif label == 'door_number_value':
                door_number_value = subtree_text
            elif label == 'door_number_unit':
                door_number_unit = subtree_text
            elif label == 'floor':
                floor = subtree_text

        return street_names, door_number_value, door_number_unit, floor

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

        condition = with_labels(['street_no_num', 'street_with_num'])

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
        self._parser = nltk.EarleyChartParser(load_grammar(GRAMMAR_PATH))

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
        normalized = self._normalization_regexp.sub(' ', address)

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

        La estructura del valor de retorno del método está definido en la
        variable ADDRESS_DATA_TEMPLATE. El valor es un diccionario que incluye
        la dirección de entrada y sus componentes separados, en casos en los
        que la extracción se pudo completar exitosamente. Por ejemplo:

        Entrada: 'Tucumán 1300 1° A'

        Salida:
        {
            "door_number": {
                "unit": null,
                "value": "1300"
            },
            "floor": "1° A",
            "street_names": [
                "Tucumán"
            ],
            "type": "simple"
        }

        Args:
            address (str): Dirección sobre la cual realizar la extracción de
                componentes.

        Returns:
            dict: Componentes de la dirección 'address'.

        """
        # Remover espacios al comienzo y al final
        address = address.strip()
        processed = self._normalize_address(address)

        data = copy.deepcopy(ADDRESS_DATA_TEMPLATE)

        if not processed:
            return data

        tokens = self._tokenize_address(processed)

        visitor = self._parse_token_types([
            t_type for _, t_type in tokens
        ])

        if visitor:
            street_names, door_number_value, door_number_unit, floor = \
                visitor.extract_data(tokens)
            data['type'] = visitor.address_type
            data['street_names'] = street_names
            data['door_number']['value'] = door_number_value
            data['door_number']['unit'] = door_number_unit
            data['floor'] = floor

        return data
