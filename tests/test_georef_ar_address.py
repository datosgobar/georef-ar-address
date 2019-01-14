import json
import os
import unittest
from unittest import TestCase
from georef_ar_address import AddressParser
from georef_ar_address.address_parser import ADDRESS_DATA_TEMPLATE


def test_file_path(filename):
    return os.path.join(os.path.dirname(__file__), filename)


class CachedAddresParserTest(TestCase):
    def test_address_parser_cache(self):
        """Al utilizar un cache, se debería agregar una key por cada
        esctructura de dirección distinta."""
        cache = {}
        parser = AddressParser(cache=cache)
        addresses = [
            'Corrientes 1000',
            'Santa fe 2000',
            'callle 10 123 y Tucumán'
        ]

        for address in addresses:
            parser.parse(address)

        self.assertEqual(len(cache), len(addresses))

    def test_address_parser_cache_same_structures(self):
        """Al utilizar un cache, y si dos direcciones comparten la misma
        estructura, solo se debería agregar una key para las dos."""
        cache = {}
        parser = AddressParser(cache=cache)
        addresses = [
            'Corrientes 1000',
            'Tucumán 2000',
            'Córdoba 3333'
        ]

        for address in addresses:
            parser.parse(address)

        self.assertEqual(len(cache), 1)


class AddressParserTest(TestCase):
    @classmethod
    def setUpClass(cls):
        cls._parser = AddressParser()

        with open(cls._test_file) as f:  # pylint: disable=no-member
            cls._test_cases = json.load(f)

        address_types = {None, 'simple', 'intersection', 'between'}

        assert all(
            test_case['type'] in address_types
            for test_case in cls._test_cases
        ) and cls._test_cases

    def assert_cases_for_type(self, address_type):
        """Dado un tipo de dirección, leer todos los casos de ese tipo del
        archivo JSON cargado, y comprobar que el parser retorna exactamente
        el valor que se espera.

        Cada test case del archivo JSON contiene un diccionario que tiene la
        misma estructura que la del valor de retorno de AddressParser.parse().
        Utilizando el método 'assert_address_data', se comprueba que el valor
        de retorno de AddressParser.parse() sea idéntico al que está escrito en
        el test case, utilizando el campo 'address' como entrada.

        Los test cases fueron almacenados en archivos JSON para evitar tener
        grandes cantidades de definiciones de variables dentro del código de
        los tests.

        Args:
            address_type (str): Tipo de dirección (None, 'simple',
                'intersection', 'between').

        """
        test_cases = [
            test_case for test_case in self._test_cases
            if test_case['type'] == address_type
        ]

        for test_case in test_cases:
            for key in ADDRESS_DATA_TEMPLATE:
                if key not in test_case:
                    test_case[key] = ADDRESS_DATA_TEMPLATE[key]

            self.assert_address_data(test_case['address'], test_case)

    def assert_address_data(self, address, data):
        parsed = self._parser.parse(address)
        parsed['address'] = address
        self.assertDictEqual(parsed, data)


class MockAddressParserTest(AddressParserTest):
    _test_file = test_file_path('test_cases.json')

    def test_none_cases(self):
        """Comprobar que los casos de tipo None son parseados
        correctamente."""
        self.assert_cases_for_type(None)

    def test_simple_cases(self):
        """Comprobar que los casos de tipo 'simple' son parseados
        correctamente."""
        self.assert_cases_for_type('simple')

    def test_intersection_cases(self):
        """Comprobar que los casos de tipo 'intersection' son parseados
        correctamente."""
        self.assert_cases_for_type('intersection')

    def test_between_cases(self):
        """Comprobar que los casos de tipo 'between' son parseados
        correctamente."""
        self.assert_cases_for_type('between')


class RealAddressParserTest(AddressParserTest):
    _test_file = test_file_path('real_cases.json')

    def test_none_cases(self):
        """Comprobar que los casos de tipo None son parseados
        correctamente."""
        self.assert_cases_for_type(None)

    def test_simple_cases(self):
        """Comprobar que los casos de tipo 'simple' son parseados
        correctamente."""
        self.assert_cases_for_type('simple')

    def test_intersection_cases(self):
        """Comprobar que los casos de tipo 'intersection' son parseados
        correctamente."""
        self.assert_cases_for_type('intersection')

    def test_between_cases(self):
        """Comprobar que los casos de tipo 'between' son parseados
        correctamente."""
        self.assert_cases_for_type('between')


class InvalidAddressesParserTest(TestCase):
    def setUp(self):
        self.parser = AddressParser()

    def test_empty_address(self):
        """Un string vacío como dirección debería tener tipo None."""
        data = self.parser.parse('')
        self.assertEqual(data['type'], None)


if __name__ == '__main__':
    unittest.main()
