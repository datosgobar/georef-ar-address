"""Módulo georef_ar_address.py

Contiene clases y funciones utilizadas para extraer información de direcciones
de calles en Argentina. Los tipos de direcciones aceptadas son:

<calle>
<calle> <altura>
<calle> y <calle>
<calle> <altura> y <calle>
<calle> y <calle> <altura>
<calle> entre <calle> y <calle>
<calle> <altura> entre <calle> y <calle>
<calle> entre <calle> y <calle> <altura>
"""

import re
import os
import copy
import nltk

GRAMMARS_DIR = os.path.join(os.path.dirname(__file__), 'grammars')
GRAMMAR_PATH = os.path.join(GRAMMARS_DIR, 'address-ar.cfg')
START_PRODUCTION = 'address'

ADDRESS_DATA_TEMPLATE = {
    'address': None,
    'street_names': [],
    'door_number': {
        'value': None,
        'unit': None
    },
    'floor': None,
    'type': 'none'
}

_SEPARATION_REGEXP = r'([^\W\d]{2,}\.?)(\d)'

_NORMALIZATION_REGEXPS = [
    r'\((ex|antes|frente|mano|(al\s)?lado).+?\)',  # Remover aclaraciones
    r'\([sneo]\)',  # Remover aclaraciones de orientación
    r',(\s|$)|\s,',  # Comas utilizadas para separar texto
    r'[()"?]',  # Caracteres no deseados
    r'-+$',  # Guiones al final
    r'\s-\s',  # Guiones entre espacios
    r'(b[°ºª]|barrio\s|bo\.\s).*',  # Indicadores de barrio
    r'\sal\s+(?=\d)'  # Palabra 'al' antes de un número
]

_TOKEN_TYPES = [
    ('AND_WORD', r'y\s(?=\D)|e\s(?=i)'),
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
    ('WORD', r'(\w|\.|\'|`|´|:|/)+'),
    ('WS', r'\s'),
    ('UNKNOWN', '.+')
]


class InvalidTokenException(Exception):
    pass


class InvalidGrammarException(Exception):
    pass


def with_labels(labels):
    return lambda t: t.label() in set(labels)


def load_grammar(grammar_path):
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

            if isinstance(element, nltk.Nonterminal):
                if symbol not in nonterminals:
                    raise InvalidGrammarException(
                        'Invalid nonterminal: {}'.format(symbol))
            elif symbol not in terminals:
                raise InvalidGrammarException(
                    'Invalid terminal: {}'.format(symbol))

    return grammar


class TreeVisitor:
    __slots__ = ['_tree', '_rank']

    def __init__(self, tree):
        self._tree = tree
        self._rank = None

    def extract_data(self, tokens):
        tree = self._tree.copy(deep=True)

        # Agregar valores reales a las hojas del árbol
        # TODO: Cachear los índices de las hojas de cada subarbol y usar
        # eso directamente.
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

        for subtree in tree.subtrees(condition):
            label = subtree.label()
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
        has_door_number = False
        unnamed_streets = 0

        condition = with_labels(['street_no_num', 'street_with_num'])
        for subtree in self._tree.subtrees(condition):
            if subtree.label() == 'street_with_num':
                has_door_number = True

            if subtree[0][0].label() == 'unnamed_street':
                unnamed_streets += 1

        if has_door_number:
            ranks = ['isct', 'simple', 'btwn']
        else:
            ranks = ['simple', 'isct', 'btwn']

        rank = ranks.index(self.address_type)

        return (unnamed_streets, int(has_door_number), rank)

    @property
    def rank(self):
        if not self._rank:
            self._rank = self._get_rank()

        return self._rank

    @property
    def address_type(self):
        return self._tree.label()


class AddressParser:
    def __init__(self, cache=None):
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
        tokens = []
        for mo in self._token_regexp.finditer(address):
            kind = mo.lastgroup
            value = mo.group().strip()

            if kind == 'UNKNOWN':
                raise InvalidTokenException('Value: {}'.format(value))
            elif kind != 'WS':
                tokens.append((value, kind))

        return tokens

    def _preprocess_address(self, address):
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
        if len(visitors) > 1:
            visitors.sort(key=lambda v: v.rank, reverse=True)

            # La lista de árboles ahora está ordenada de mejor a peor. Comparar
            # el rank (puntaje) del primer elemento con el del segundo: si son
            # iguales, entonces hay dos (o más) árboles con el mismo puntaje
            # maximal. Esto quiere decir que todos estos árboles son una
            # solución viable, pero no es posible distinguir cuál de ellos es
            # el más adecuado. Si sucede esto, devolver None.
            if visitors[0].rank == visitors[1].rank:
                return None

        return visitors[0]

    def _tokens_parse_tree(self, token_types):
        visitors = [
            TreeVisitor(tree[0])  # tree['address']
            for tree in
            self._parser.parse(token_types)
        ]

        return self._disambiguate_trees(visitors) if visitors else None

    def _parse_token_types(self, token_types):
        if self._cache is not None:
            tokens_hash = hash(tuple(token_types))

            if tokens_hash in self._cache:
                return self._cache[tokens_hash]

            tree = self._tokens_parse_tree(token_types)
            self._cache[tokens_hash] = tree
            return tree

        return self._tokens_parse_tree(token_types)

    def parse(self, address):
        # Remover espacios al comienzo y al final
        address = address.strip()
        processed = self._preprocess_address(address)

        data = copy.deepcopy(ADDRESS_DATA_TEMPLATE)
        data['address'] = address

        if not processed:
            return data

        try:
            tokens = self._tokenize_address(processed)
        except InvalidTokenException:
            return data

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
