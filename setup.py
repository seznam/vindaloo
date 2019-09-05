from setuptools import setup
setup(
    name='vindaloo',
    version='2.2.0',
    description='K8S deployer',
    author='Daniel Milde',
    author_email='daniel.milde@firma.seznam.cz',
    install_requires=[
        'argcomplete>=1.9.5',
        'pystache',
        'typing',
    ],
    entry_points={
        'console_scripts': [
            'vindaloo = vindaloo.vindaloo:run'
        ]
    },
    packages=['vindaloo'],
    classifiers=[
        'Programming Language :: Python :: 3',
    ],
)
