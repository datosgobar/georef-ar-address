"""Módulo '__main__' de georef-ar-address.

Define una función para probar la librería de forma interactiva.

"""

from .address_parser import AddressParser


def address_parser_repl():
    """Función de prueba para probar ejemplos de direcciones en la consola."""
    import json
    parser = AddressParser(cache={})

    while True:
        try:
            address = input('> ')
        except (KeyboardInterrupt, EOFError):
            break

        if not address:
            break

        data = parser.parse(address)
        print(json.dumps(data, indent=4, ensure_ascii=False, sort_keys=True))

    print()


address_parser_repl()
