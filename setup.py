from distutils.core import setup

VERSION = '0.0.9'


with open('requirements.txt') as f:
    requires = f.read().splitlines()

with open('README.md') as f:
    long_description = f.read()

setup(
    name='georef-ar-address',
    packages=['georef_ar_address'],
    version=VERSION,
    description='Librería escrita en Python para la identificación de componentes de direcciones argentinas',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Datos Argentina',
    author_email='datos@modernizacion.gob.ar',
    install_requires=requires,
    include_package_data=True,
    package_data={'georef_ar_address': ['grammars/*.cfg']},
    python_requires='>=3',
    url='https://github.com/datosgobar/georef-ar-address',
    download_url='https://github.com/datosgobar/georef-ar-address/archive/{}.tar.gz'.format(VERSION),
    keywords=['georef', 'datos', 'argentina', 'direccion', 'calle', 'altura', 'json', 'nltk'],
    license='MIT',
    classifiers=[
        'Programming Language :: Python :: 3 :: Only',
        'License :: OSI Approved :: MIT License',
        'Topic :: Text Processing',
        'Topic :: Software Development :: Libraries'
    ]
)
