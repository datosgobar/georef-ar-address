"""Módulo '__main__' de georef-ar-address.

Define una función para probar la librería de forma interactiva.

"""

from .address_parser import AddressParser


def address_parser_repl():
    """Función de prueba para probar ejemplos de direcciones en la consola."""
    import json
    parser = AddressParser(cache={})

    print('Ingresar una dirección y presionar [ENTER] para extraer '
          'sus componentes.')
    while True:
        try:
            address = input('> ')
        except (KeyboardInterrupt, EOFError):
            break

        if not address:
            break

        data = parser.parse(address)
        if data:
            print(json.dumps(data.to_dict(), indent=4, ensure_ascii=False,
                             sort_keys=True))
        else:
            print('Error: dirección inválida.')

    print()


address_parser_repl()
