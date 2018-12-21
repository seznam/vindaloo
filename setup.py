from setuptools import setup
setup(
    name='szn-vindaloo',
    version='1.13.2',
    description='K8S deployer',
    author='Daniel Milde',
    author_email='daniel.milde@firma.seznam.cz',
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
    include_package_data=True,
    classifiers=[
        'Programming Language :: Python :: 3',
    ],
)
