# georef-ar-address
[![Build Status](https://travis-ci.org/datosgobar/georef-ar-address.svg?branch=master)](https://travis-ci.org/datosgobar/georef-ar-address)
[![Coverage Status](https://coveralls.io/repos/github/datosgobar/georef-ar-address/badge.svg?branch=master)](https://coveralls.io/github/datosgobar/georef-ar-address?branch=master)
![](https://img.shields.io/github/license/datosgobar/georef-ar-address.svg)
![https://pypi.org/project/georef-ar-address/](https://img.shields.io/pypi/v/georef-ar-address.svg)
![](https://img.shields.io/badge/python-3-blue.svg)

Librería escrita en Python 3 para la identificación de componentes de direcciones argentinas.

## Objetivo

El objetivo de la librería `georef-ar-address` es, dada una dirección en forma de string como entrada, extraer todas las componentes que la componen. **Todo el procesamiento se hace de forma local, sin consultar recursos externos.** Con la librería se intenta cubrir la mayor cantidad de tipos de direcciones posibles, teniendo en cuenta las distintas estructuras que pueden tomar las mismas, así también como errores comunes de escritura, presencia de datos innecesarios y ambigüedades.

Como ejemplo, utilizar la librería sobre la dirección:

`Av. Libertador N1331 2ndo A e/25 de Mayo y Bartolomé Mitre`

Resultaría en la siguiente extracción de componentes:
```json
{
    "door_number": {
        "unit": "N",
        "value": "1331"
    },
    "floor": "2ndo A",
    "street_names": [
        "Av. Libertador",
        "25 de Mayo",
        "Bartolomé Mitre"
    ],
    "type": "between"
}
```

## Instalación

La librería se encuentra publicada en [`PyPI`](https://pypi.org/project/georef-ar-address/), y puede ser instalada utilizando `pip`:

```bash
$ pip3 install georef-ar-address
```

## Uso Rápido

Para probar ejemplos de extracción de componentes de forma interactiva, utilizar el siguiente comando:
```bash
$ python -m georef_ar_address
```

Una vez ejecutado el comando se puede escribir una dirección y presionar ENTER para obtener las componentes de la misma.

## Documentación

Para utilizar la librería desde Python, se debe instanciar un objeto de tipo `AddressParser` y utilizar su método `parse`, pasando una dirección como argumento:

```python
>>> from georef_ar_address import AddressParser
>>> parser = AddressParser()
>>> parser.parse('Sarmiento N° 1100')
{
    "door_number": {
        "unit": "N°",
        "value": "1100"
    },
    "floor": None,
    "street_names": [
        "Sarmiento"
    ],
    "type": "simple"
}
```

El valor de retorno de `parse` es una instancia de `dict` conteniendo cada componente de la dirección, en caso de una extracción exitosa. Los valores del diccionario son los siguientes:

- `door_number` `unit`: Unidad de la altura de la dirección (e.g. `N°`, `nro.`, `Km`).
- `door_number` `value`: Valor de la altura de la dirección (e.g. `132`, `400/401`, `S/N`)
- `floor`: Piso de la dirección (e.g. `2ndo B`, `PB`).
- `street_names`: Lista de nombres de calles contenidos en la dirección (e.g. `Santa Fe`, `Ruta 4`).
- `type`: Tipo de dirección detectado. Los valores posibles son:
  - `simple`: Dirección compuesta de un nombre de calle y una altura opcional.
  - `intersection`: Dirección compuesta de dos nombres de calles en forma de intersección, con altura opcional.
  - `between`: Dirección compuesta de tres nombres de calles, especificando una posición sobre una entre otras dos, con altura opcional.
  - `None`: Dirección de entrada inválida o ambigua.

Todos los valores del diccionario son de tipo `str`, o toman el valor de `None`.

El inicializador de la clase `AddressParser` acepta un parámetro `cache` de tipo `dict` (o equivalente), que le permite cachear internamente resultados de parseos para acelerar el procesamiento de direcciónes con estructuras similares.

## Diseño

Para leer sobre las desiciones de diseño y funcionamiento de `georef-ar-address`, ver el archivo [**design.md**](docs/design.md).

Para consultar el historial de versiones de `georef-ar-address`, ver el archivo [**history.md**](docs/history.md).

## Soporte
En caso de que encuentres algún bug, tengas problemas con la instalación, o tengas comentarios de alguna parte de `georef-ar-address`, podés mandarnos un mail a [datos@modernizacion.gob.ar](mailto:datos@modernizacion.gob.ar) o [crear un issue](https://github.com/datosgobar/georef-ar-address/issues/new?title=Encontre-un-bug-en-georef-ar-address).
