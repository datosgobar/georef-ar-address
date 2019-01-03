# Makefile para georef-ar-address
#
# Contiene recetas para ejecutar tests y linters de código.

test:
	python -m unittest

code_checks:
	flake8 georef_ar_address.py tests/test_georef_ar_address.py
	pylint georef_ar_address.py tests/test_georef_ar_address.py
