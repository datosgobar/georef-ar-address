"""Módulo address_data.py de georef-ar-address

Contiene la clase 'AddressData', utilizada para almacenar, simplificar y
presentar de forma estandarizada los datos producidos por la clase
'AddressParser'.

"""

ADDRESS_TYPES = ['simple', 'intersection', 'between']


class AddressData:
    """Contiene las componentes de una dirección, luego de ser extraídas
    mediante el método 'parse()' de 'AddressParser'.

    Attributes:
        _type (str): Tipo de la dirección.
        _street_names (list): Lista de nombres de calles de la dirección.
        _door_number_value (str): Valor de la altura de la dirección.
        _door_number_unit (str): Unidad de la altura de la dirección.
        _floor (str): Piso de la dirección.

    """

    __slots__ = [
        '_type',
        '_street_names',
        '_door_number_value',
        '_door_number_unit',
        '_floor'
    ]

    def __init__(self, address_type, street_names=None, door_number=None,
                 floor=None):
        """Inicializa un objeto de tipo 'AddressData'.

        Args:
            address_type (str): Ver atributo '_type'.
            street_names (list): Ver atributo '_street_names'.
            door_number (tuple): Tupla de (str, str), donde el primer elemento
                se asigna a '_door_number_value' y el segundo a
                '_door_number_unit'.
            floor (str): Ver atributo '_floor'.

        Raises:
            ValueError: Si el tipo de dirección no es válido.

        """
        if address_type not in ADDRESS_TYPES:
            raise ValueError('Unknown address type: {}'.format(address_type))

        self._type = address_type
        self._street_names = street_names or []
        self._door_number_value = door_number[0] if door_number else None
        self._door_number_unit = door_number[1] if door_number else None
        self._floor = floor

    def to_dict(self):
        """Devuelve una representación del objeto en forma de diccionario. Útil
        para cuando es necesario serializar el objeto a formatos como JSON u
        otros. La estructura del diccionario es la siguiente:

        Entrada: AddressData de 'Tucumán 1300 1° A'

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

        Returns:
            dict: Diccionario con los componentes de la direccion.

        """
        return {
            'type': self._type,
            'street_names': self._street_names,
            'door_number': {
                'value': self._door_number_value,
                'unit': self._door_number_unit
            },
            'floor': self._floor
        }

    @property
    def type(self):
        return self._type

    @property
    def street_names(self):
        return self._street_names

    @property
    def door_number_value(self):
        return self._door_number_value

    @property
    def door_number_unit(self):
        return self._door_number_unit

    @property
    def floor(self):
        return self._floor

    def __repr__(self):
        return 'AddressData({})'.format(self.to_dict())
