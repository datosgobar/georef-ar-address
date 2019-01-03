import json
import os
from unittest import TestCase
from georef_ar_address import AddressParser
from georef_ar_address.address_parser import ADDRESS_DATA_TEMPLATE


def test_file_path(filename):
    return os.path.join(os.path.dirname(__file__), filename)


class BaseClasses:
    class AddressParserTest(TestCase):
        @classmethod
        def setUpClass(cls):
            cls._parser = AddressParser(cache={})

            with open(cls._test_file) as f:  # pylint: disable=no-member
                cls._test_cases = json.load(f)

            assert cls._test_cases

        def test_none_cases(self):
            self.assert_address_cases('none')

        def test_simple_cases(self):
            self.assert_address_cases('simple')

        def test_isct_cases(self):
            self.assert_address_cases('isct')

        def test_btwn_cases(self):
            self.assert_address_cases('btwn')

        def assert_address_cases(self, address_type):
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


class MockAddressParserTest(BaseClasses.AddressParserTest):
    _test_file = test_file_path('test_cases.json')


class RealAddressParserTest(BaseClasses.AddressParserTest):
    _test_file = test_file_path('real_cases.json')
