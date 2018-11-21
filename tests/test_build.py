import sys

from utils import chdir


def test_build_all(loo):
    # nafakujeme parametry
    sys.argv = ['vindaloo', '--noninteractive', 'build']

    with chdir('tests'):
        loo.main()

    # zkontrolujeme s jakymi parametry byl zavolan docker
    assert loo.cmd.call_args_list == [
        (([
            'docker',
            'build',
            '-t', 'doc.ker.dev.dszn.cz/test/foo:1.0.0',
            '--no-cache',
            '-f', 'Dockerfile',
            '.'
        ],),),
        (([
            'docker',
            'build',
            '-t', 'doc.ker.dev.dszn.cz/test/bar:2.0.0',
            '--no-cache',
            '-f', 'Dockerfile',
            '.'
        ],),),
    ]

    # zkontrolujeme vygenerovany Dockerfile
    with open('tests/Dockerfile', 'r') as fp:
        assert fp.read() == """LABEL maintainer="Test Test <test.test@firma.seznam.cz>"
LABEL description="Bar"
LABEL version="2.0.0"
"""


def test_build_one(loo):
    sys.argv = ['vindaloo', '--noninteractive', 'build', 'test/foo']

    with chdir('tests'):
        loo.main()

    # zkontrolujeme s jakymi parametry byl zavolan docker
    assert loo.cmd.call_args_list == [
        (([
            'docker',
            'build',
            '-t', 'doc.ker.dev.dszn.cz/test/foo:1.0.0',
            '--no-cache',
            '-f', 'Dockerfile',
            '.'
        ],),),
    ]

    # zkontrolujeme vygenerovany Dockerfile
    with open('tests/Dockerfile', 'r') as fp:
        assert fp.read() == """FROM debian

LABEL maintainer="Test Test <test.test@firma.seznam.cz>"
LABEL description="Foo"
LABEL version="1.0.0"
"""


def test_build_latest(loo):
    sys.argv = ['vindaloo', '--noninteractive', 'build', '--latest', 'test/foo']

    with chdir('tests'):
        loo.main()

    # zkontrolujeme s jakymi parametry byl zavolan docker
    assert loo.cmd.call_args_list == [
        (([
            'docker',
            'build',
            '-t', 'doc.ker.dev.dszn.cz/test/foo:1.0.0',
            '--no-cache',
            '-t', 'doc.ker.dev.dszn.cz/test/foo:latest',
            '-f', 'Dockerfile',
            '.'
        ],),),
    ]

    # zkontrolujeme vygenerovany Dockerfile
    with open('tests/Dockerfile', 'r') as fp:
        assert fp.read() == """FROM debian

LABEL maintainer="Test Test <test.test@firma.seznam.cz>"
LABEL description="Foo"
LABEL version="1.0.0"
"""


def test_build_latest_with_cache(loo):
    sys.argv = ['vindaloo', '--noninteractive', 'build', '--cache', '--latest', 'test/foo']

    with chdir('tests'):
        loo.main()

    # zkontrolujeme s jakymi parametry byl zavolan docker
    assert loo.cmd.call_args_list == [
        (([
            'docker',
            'build',
            '-t', 'doc.ker.dev.dszn.cz/test/foo:1.0.0',
            '-t', 'doc.ker.dev.dszn.cz/test/foo:latest',
            '-f', 'Dockerfile',
            '.'
        ],),),
    ]

    # zkontrolujeme vygenerovany Dockerfile
    with open('tests/Dockerfile', 'r') as fp:
        assert fp.read() == """FROM debian

LABEL maintainer="Test Test <test.test@firma.seznam.cz>"
LABEL description="Foo"
LABEL version="1.0.0"
"""
