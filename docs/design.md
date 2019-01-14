# georef-ar-address - Diseño e Implementación

## Teoría

El objetivo de la librería `georef-ar-address` es extraer de un string conteniendo una dirección las componentes individuales que la componen, realizando todo el procesamiento localmente. Es importarte resaltar que la entrada (input) utilizada es un string común, sin ningún tipo de metadatos que puedan proveer información sobre su contenido. Para simplificar el proceso de extracción, se definieron tres tipos de direcciones posibles a aceptar como entrada:

- `simple`: nombre de calle y altura opcional (con piso opcional)
- `isct`: intersección de calles, con altura opcional (con piso opcional)
- `btwn`: nombre de calle y altura opcional (con piso opcional) entre otras dos
  calles.
- `None`: utilizado para representar direcciones que no pudieron ser procesadas

Habiendo dicho esto, las componentes que se desean extraer de las direcciones
son:

- Nombres de calles (pueden haber una, dos o tres en total)
- Altura (su valor, y su tipo/unidad) (opcional)
- Piso (opcional)
- Tipo de dirección

Como ejemplo, la dirección:

    Santa Fe N° 1004, 2ndo B

Esta compuesta de las siguientes componentes:

    calles:          "Santa Fe"
    altura (unidad): "N°"
    altura (valor):  "1004"
    piso:            "2ndo B"
    tipo:            "simple"

Otro ejemplo:

    Tucumán y 9 de Julio

Esta compuesta de las siguientes componentes:

    calles:          "Tucumán", "9 de Julio"
    altura (unidad): (no tiene)
    altura (valor):  (no tiene)
    piso:            (no tiene)
    tipo:            "isct" (intersección)

Y un último ejemplo:

    Av. 15 de Mayo al 3133 entre Calle 11 y Vicente Lopez y Planes

Esta compuesta de las siguientes componentes:

    calles:          "Av. 15 de Mayo", "Calle 11", "Vicente Lopez y Planes"
    altura (unidad): (no tiene)
    altura (valor):  3133
    piso:            (no tiene)
    tipo:            "btwn" (calle entre calles)

## Diseño

La extracción de componentes está compuesta de 5 pasos:

1) Normalización
2) Tokenización
3) Parseo
4) Desambiguación
5) Ensamblado

A continuación, se explica brevemente cómo funciona cada paso, y qué parte del
código es responsable por su funcionamiento.

### 1) Normalización

**INPUT:** string original

En el paso de normalización, se remueven partes del string de entrada que no son de utilidad o que no representan información útil. También se corrigen errores comunes como por ejemplo secuencias de letras pegadas a números. El procesamiento se realiza utilizando expresiones regulares.

**OUTPUT:** string normalizado

### 2) Tokenización

**INPUT:** string normalizado

El en paso de tokenización, se transforma el string de entrada a una lista de tokens. Un token es una tupla de `(valor, TIPO)`, donde "valor" es un valor extraído del string de entrada, y `TIPO` es un tipo que se le asigna a ese valor, dependiendo de su contenido. Por ejemplo, el valor "hola" tiene el tipo `WORD`, mientras que "432" tiene el tipo `NUM`. La lista de tokens se genera dividiendo el string de entrada en partes (separando por espacios) y asignando cada parte resultante a un tipo de token.

Como ejemplo, el string de entrada "Santa Fe 1000" resultaría en la siguiente lista de tokens: `[("Santa", "WORD"), ("Fe", "WORD"), ("1000", "NUM")]`.

**OUTPUT:** lista de tokens

### 3) Parseo

**INPUT:** lista de tokens

En el paso de parseo, se toma la lista de tipos tokens y se intenta construir un árbol de parseo utilizando la gramática libre de contexto definida en el archivo "address-ar.cfg". El parseo se realiza utilizando la clase `EarleyChartParser` de la librería de procesamiento de lenguaje natural NLTK.

Es importante notar que se utilizan solo los tipos de los tokens en el momento de parseo. En el ejemplo anterior, se utilizaría la lista `["WORD", "WORD", "NUM"]` como entrada a la instancia de `EarleyChartParser`. Esto se debe a que la gramática definida solo contempla los tipos de los tokens, y no sus valores reales, que no son de importancia en el momento del parseo. El hecho de poder considerar las palabras "Juan" y "María" como `WORD` (por jemplo) simplifica enormemente la definición de la gramática, y obtiene los mismos resultados.

El parseo puede resultar en una lista vacía, o en una lista con cualquier cantidad de parseos posibles para la lista de tipos de tokens dada.

**OUTPUT:** lista de árboles de parseo

### 4) Desambiguación

**INPUT:** lista de árboles de parseo

En el paso de desambiguación, se toman todos los árboles de parseo obtenidos, y se elige el mejor, basándose en tres distintos criterios:

Se priorizan árboles que hayan encontrado calles "sin nombre", es decir, calles del estilo "Calle 33" o "Avenida 11", ya que de esta forma se evita interpretar los números como alturas.

Se priorizan también los árboles que posean alturas, para evitar interpretar "Rosario 1003" como una calle llamada "Rosario 1003", en lugar de una calle llamada "Rosario" con altura "1003".

Finalmente, dependiendo de si se encontró una altura o no, se le asigna al árbol una prioridad adicional, dependiente del tipo de dirección encontrado. Las direcciones de tipo `btwn` siempre tienen mayor prioridad ya que poseen una estructura más compleja y su presencia normalmente indica que la dirección efectivamente es de tipo `btwn`.

Si el árbol de parseo contiene una altura, se prioriza luego las direcciones de tipo `simple`, y finalmente las de tipo `isct`. En caso de no contener una altura, el orden de los dos tipos se intercambian. Este orden permite interpretar direcciones como "Vicente Lopez y Planes 120" como tipo `simple` (y no como tipo `isct`, a pesar de contener una "y"). Un problema generado por esto es que direcciones como "Tucumán y Belgrano 1231" son interpretadas como `simple` y no `isct`. Aunque en algunos casos es posible evitar el error, pogramáticamente no hay mucho que se pueda hacer para asegurarse de que no se suceda. De todas formas, en listados de direcciones utilizados durante el desarrollo de la librería, la cantidad de direcciones encontradas con esa estructura fue menor al 1%. Cuando el árbol no contiene una altura, se interpreta "Mitre y Misiones" como `isct`.

El orden de los criterios mencionados es importante. Los primeros criterios tienen más importancia que los últimos. Este orden fue determinado experimentalmente, probando con varios ejemplos de direcciones reales hasta hallar la mejor opción.

**OUTPUT:** árbol de parseo, o `None`

### 5) Ensamblado

**INPUT:** árbol de parseo

Finalmente, en el paso de ensamblado se toma el mejor árbol elegido, y se lo utiliza para identificar las componentes de la dirección contenida en el string de entrada original. Para lograr esto, se recorre el árbol (*preorder*, izquierda a derecha) buscando nodos conteniendo nombres de calles, alturas, etc. y se calcula a qué parte del string original pertenecen. Las componentes resultantes se insertan en un diccionario (`dict`), y se devuelve la información al usuario.

**OUTPUT:** diccionario con componentes de la dirección

### Manejo de Errores

Si el string de entrada contiene un valor que no puede ser interpretado como una dirección, se retorna `None` como tipo de dirección. Esto puede suceder si se encotraron dos o más interpretaciones posibles del contenido del string, y no se pudo decidir cuál fue la correcta (en el paso de desambiguación).

## Performance
La clase `AddressParser` incluye la opción de especificar un objeto `cache` a utilizar como cache durante el proceso de extracción. El objeto debe ser una instancia de `dict`, o bien un objeto que se comporte como un `dict`. Para realizar el cacheo, se toma la cadena de tipos de tokens recibidos en la etapa 3 (parseo), se los *hashea* y luego se los asigna a la salida de la etapa 4 (desambiguación). De esta forma, cuando se reciben dos direcciones que generan la misma lista de tipos de tokens, se reutiliza el mejor árbol de parseo y se evita tener que realizar un parseo nuevo. Como ejemplo, las siguientes dos direcciones:

- Córdoba 1321, 2° B
- Tucumán 312, 1 A

Generan la misma lista de tipos de tokens:

`[WORD, NUM, NUM, LETTER]`

De esta forma, durante la extracción de componentes de la segunda dirección se utilizaría el árbol generado durante la extracción de la primera.
