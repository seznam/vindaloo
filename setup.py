from vindaloo.vindaloo import VERSION

from distutils.core import setup
setup(
    name='vindaloo',
    version=VERSION,
    install_requires=[
        'argcomplete',
        'pystache',
        'typing',
    ],
    entry_points={
        'console_scripts': [
            'vindaloo = vindaloo.vindaloo:run'
        ]
    },
    packages=['vindaloo'],
    include_package_data=True
)
