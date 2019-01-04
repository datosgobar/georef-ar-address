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

        assert cls._test_cases

    def assert_cases_for_type(self, address_type):
        """Dado un tipo de dirección, leer todos los casos de ese tipo del
        archivo JSON cargado, y comprobar que el parser retorna exactamente
        el valor que se espera.

        Cada test case del archivo JSON contiene un diccionario que tiene la
        misma estructura que la del valor de retorno de AddressParser.parse().
        Utilizando el método 'assert_address_data', se comprueba que el valor
        de retorno de AddressParser.parse() sea idéntico al que está escrito en
        el test case, utilizando el campo 'address' como entrada.

        Args:
            address_type (str): Tipo de dirección ('none', 'simple', 'isct',
                'btwn').

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
        self.assertDictEqual(parsed, data)


class MockAddressParserTest(AddressParserTest):
    _test_file = test_file_path('test_cases.json')

    def test_none_cases(self):
        """Comprobar que los casos de tipo 'none' son parseados
        correctamente."""
        self.assert_cases_for_type('none')

    def test_simple_cases(self):
        """Comprobar que los casos de tipo 'simple' son parseados
        correctamente."""
        self.assert_cases_for_type('simple')

    def test_isct_cases(self):
        """Comprobar que los casos de tipo 'isct' son parseados
        correctamente."""
        self.assert_cases_for_type('isct')

    def test_btwn_cases(self):
        """Comprobar que los casos de tipo 'btwn' son parseados
        correctamente."""
        self.assert_cases_for_type('btwn')


class RealAddressParserTest(AddressParserTest):
    _test_file = test_file_path('real_cases.json')

    def test_none_cases(self):
        """Comprobar que los casos de tipo 'none' son parseados
        correctamente."""
        self.assert_cases_for_type('none')

    def test_simple_cases(self):
        """Comprobar que los casos de tipo 'simple' son parseados
        correctamente."""
        self.assert_cases_for_type('simple')

    def test_isct_cases(self):
        """Comprobar que los casos de tipo 'isct' son parseados
        correctamente."""
        self.assert_cases_for_type('isct')

    def test_btwn_cases(self):
        """Comprobar que los casos de tipo 'btwn' son parseados
        correctamente."""
        self.assert_cases_for_type('btwn')


if __name__ == '__main__':
    unittest.main()
