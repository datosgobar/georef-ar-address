# Makefile para georef-ar-address
#
# Contiene recetas para ejecutar tests y empaquetar la librería.

test:
	python -m unittest

coverage:
	coverage run --source=georef_ar_address --omit=georef_ar_address/__main__.py \
		-m tests.test_georef_ar_address

code_checks:
	flake8 georef_ar_address/*.py tests/*.py
	pylint georef_ar_address/*.py tests/*.py

package:
	mkdir -p dist
	rm -rf dist/*
	python setup.py sdist

upload: package
	twine upload dist/*

repl:
	@python georef_ar_address/address_parser.py
