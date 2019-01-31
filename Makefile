# Makefile para georef-ar-address
#
# Contiene recetas para ejecutar tests y empaquetar la librería.

test:
	LOG_LEVEL=DEBUG python -m unittest

coverage:
	coverage run --source=georef_ar_address --omit=georef_ar_address/__main__.py \
		-m tests.test_georef_ar_address
	coverage report

code_checks:
	flake8 georef_ar_address/*.py tests/*.py tools/*.py
	pylint georef_ar_address/*.py tests/*.py tools/*.py

benchmark:
	PYTHONPATH=$$(pwd) python tools/benchmark.py

package:
	mkdir -p dist
	rm -rf dist/*
	python setup.py sdist

upload: package
	twine upload dist/*

repl:
	@python -m georef_ar_address
