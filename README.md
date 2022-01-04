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
```
street_names:        ["Av. Libertador", "25 de Mayo", "Bartolomé Mitre"]
door_number.value:   "1331"
door_number.unit:    "N"
floor:               "2ndo A"
type:                "between"
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
AddressData({
    "street_names": [
        "Sarmiento"
    ],
    "door_number": {
        "value": "1100",
        "unit": "N°"
    },
    "floor": None,
    "type": "simple"
})
```

El valor de retorno de `parse` es una instancia de `AddressData` conteniendo cada componente de la dirección, en caso de una extracción exitosa. Los campos del objeto `AddressData` son los siguientes:

- `.street_names` *(list)*: Lista de nombres de calles contenidos en la dirección (e.g. `Santa Fe`, `Ruta 4`).
- `.door_number_value` *(str)*: Valor de la altura de la dirección (e.g. `132`, `400/401`, `S/N`)
- `.door_number_unit` *(str)*: Unidad de la altura de la dirección (e.g. `N°`, `nro.`, `Km`).
- `.floor` *(str)*: Piso de la dirección (e.g. `2ndo B`, `PB`).
- `.type` *(str)*: Tipo de dirección detectado. Los valores posibles son:
  - `simple`: Dirección compuesta de un nombre de calle y una altura opcional.
  - `intersection`: Dirección compuesta de dos nombres de calles en forma de intersección, con altura opcional.
  - `between`: Dirección compuesta de tres nombres de calles, especificando una posición sobre una entre otras dos, con altura opcional.

El inicializador de la clase `AddressParser` acepta un parámetro `cache` de tipo `dict` (o equivalente), que le permite cachear internamente resultados de parseos para acelerar el procesamiento de direcciónes con estructuras similares.

## Precisión

La librería `georef-ar-address` (versión `0.0.5`) fue utilizada sobre varios listados de direcciones para poder estimar su precisión al momento de extraer componentes. A continuación, se explica el origen de cada listado y la fidelidad de los datos devueltos por la libería en cada caso:

### Listado de datos abiertos

El primer listado de direcciones que se construyó utiliza varias fuentes provenientes de distintos portales de datos abiertos del país, incluyendo el [Portal Nacional de Datos Abiertos](https://datos.gob.ar/). Se verificó que cada archivo utilizado posea un solo campo de dirección, sin tener la calle separada de la altura.

El listado construido tiene aproximadamente 91000 direcciones. Se utilizó la librería sobre cada una, y los resultados fueron los siguientes:

 - Direcciones categorizadas (no `None`): 95.1%
 - **Aproximado de categorizaciones correctas: 88%**

Para calcular el aproximado de categorizaciones correctas, se tomaron tres muestras de cien direcciones cada una, y se inspeccionó manualmente el resultado brindado por la librería para comprobar que la extración de datos fue correcta. El porcentaje aproximado de 88% categorizaciones correctas es esperado ya que el listado de direcciones construido es muy irregular y contiene grandes cantidades de direcciones escritas de formas impredecibles (es poco uniforme). Esto se debe a que el listado se construyó a partir de datos provenientes de más de 60 archivos distintos, cada uno potencialmente de una fuente distinta.

### Listado de supermercados

El segundo listado de direcciones probado fue el archivo [carrefour.csv](https://gist.github.com/mgaitan/9677204), que contiene la dirección de 325 sucursales del supermercado Carrefour. Los resultados fueron los siguientes:

 - Direcciones categorizadas (no `None`): 99.3%
 - **Categorizaciones correctas: 97.5%**

En este caso, se categorizaron correctamente el 97.5% de las direcciones. El resultado fue comprobado manualmente.

### Listado de sucursales del Banco Nación

El tercer listado de direcciones probado fue el de las [sucursales del Banco de la Nación Argentina](http://www.agencia.mincyt.gob.ar/upload/listado_de_sucursales_bna_web.xls), con 617 elementos. Los resultados fueron los siguientes:

 - Direcciones categorizadas (no `None`): 100%
 - **Categorizaciones correctas: 97.7%**

En este caso, se categorizaron correctamente el 97.7% de las direcciones. El resultado fue comprobado manualmente.

## Diseño

Para leer sobre las desiciones de diseño y funcionamiento de `georef-ar-address`, ver el archivo [**design.md**](docs/design.md).

Para consultar el historial de versiones de `georef-ar-address`, ver el archivo [**history.md**](docs/history.md).

## Soporte
En caso de que encuentres algún bug, tengas problemas con la instalación, o tengas comentarios de alguna parte de `georef-ar-address`, podés mandarnos un mail a [datosargentina@jefatura.gob.ar](mailto:datosargentina@jefatura.gob.ar) o [crear un issue](https://github.com/datosgobar/georef-ar-address/issues/new?title=Encontre-un-bug-en-georef-ar-address).
