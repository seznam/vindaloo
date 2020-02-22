import re

from setuptools import setup


with open("vindaloo/vindaloo.py", "rt", encoding="utf8") as f:
    version = re.search(r'VERSION = \'(.*?)\'', f.read()).group(1)

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name='vindaloo',
    version=version,
    description='K8S deployer',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/seznam/vindaloo",
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
    python_requires='>=3.5',
)
