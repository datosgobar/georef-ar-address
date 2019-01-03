# Makefile para georef-ar-address
#
# Contiene recetas para ejecutar tests y empaquetar la librería.

test:
	python -m unittest

code_checks:
	flake8 georef_ar_address/*.py tests/*.py
	pylint georef_ar_address/*.py tests/*.py

package:
	mkdir -p dist
	rm -rf dist/*
	python setup.py sdist

upload: package
	twine upload dist/*
