from vindaloo.vindaloo import VERSION

from distutils.core import setup
setup(
    name='vindaloo',
    version=VERSION,
    install_requires=[
        'pystache',
    ],
    packages=['vindaloo']
)
