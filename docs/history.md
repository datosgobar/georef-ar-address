# Historial de versiones para `georef-ar-address`

## **0.0.5** - 2019/01/14
- Modifica los nombres de los tipos de direcciones `btwn` a `between` e `isct` a `intersection`.
- Remueve restricciones a caracteres aceptados por el método `parse()`: las direcciones como "sÃnta fe 1000" ahora son válidas. Este cambio facilita el procesamiento de direcciones con caracteres erróneos causados por problemas de codificado.
- Corrige interpretación de casos `intersection` donde la segunda calle comienza con "hy" o "y".

## **0.0.4** - 2019/01/10
- El tipo de las direcciones inválidas ahora es `None` en lugar del string `'none'`.

## **0.0.3** - 2019/01/09
- Permite direcciones de tipo `simple` con detalles de ubicación al final. Las siguientes direcciones ahora son interpretadas correctamente:
	- "Periodista Prieto 123 - Partido Lanús"
	- "Ruta 33 s/n Villa Chacón"
- Corrige interpretación de casos `isct` donde la segunda dirección comienza con "h" y se utiliza "e" para separar los nombres, por ejemplo: "Córdoba e Hipólito Yrigoyen".
- Remueve campo `address` redundante de la respuesta de `AddressParser.parse()`.

## **0.0.2** - 2019/01/07
- Agrega uso interactivo con `python3 -m georef_ar_address`.
- Agrega documentación de uso.

## **0.0.1** - 2019/01/04
- Versión inicial.
