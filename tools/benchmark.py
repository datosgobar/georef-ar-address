import timeit
from georef_ar_address import AddressParser

ITERATIONS = 500


def benchmark(use_cache):
    parser = AddressParser({} if use_cache else None)

    def test_fn():
        parser.parse('Tucuman')
        parser.parse('Tucuman 1000')
        parser.parse('Tucuman Nro 1000')
        parser.parse('Tucuman Nro 1000 2 c')
        parser.parse('Tucuman y Salta')
        parser.parse('Tucuman y Salta 1000')
        parser.parse('Tucuman 1000 y Salta')
        parser.parse('Tucuman e/ Corrientes y Salta')
        parser.parse('Tucuman e/ Corrientes y Salta 1000')
        parser.parse('Tucuman 1000 e/ Corrientes y Salta')

    result = timeit.timeit(stmt=test_fn, number=ITERATIONS)

    print('- Total:         {0:.7f}'.format(result))
    print('- Por iteración: {0:.7f}'.format(result / ITERATIONS))
    print('- Por dirección: {0:.7f}'.format((result / ITERATIONS) / 10))


if __name__ == '__main__':
    print('Sin Cache:')
    benchmark(False)
    print('Con Cache:')
    benchmark(True)
