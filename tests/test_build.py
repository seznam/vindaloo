import sys

from utils import chdir


def test_build_all(loo):
    # fake parameters
    sys.argv = ['vindaloo', '--noninteractive', 'build']

    with chdir('tests/test_roots/simple'):
        loo.main()

    # check the parameters docker was called with
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

    # check generated Dockerfile
    with open('tests/test_roots/simple/Dockerfile', 'r') as fp:
        assert fp.read() == """LABEL maintainer="Test Test <test.test@firma.seznam.cz>"
LABEL description="Bar"
LABEL version="2.0.0"
"""


def test_build_one(loo):
    sys.argv = ['vindaloo', '--noninteractive', 'build', 'test/foo']

    with chdir('tests/test_roots/simple'):
        loo.main()

    # check the parameters docker was called with
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

    # check generated Dockerfile
    with open('tests/test_roots/simple/Dockerfile', 'r') as fp:
        assert fp.read() == """FROM debian

LABEL maintainer="Test Test <test.test@firma.seznam.cz>"
LABEL description="Foo"
LABEL version="1.0.0"
"""


def test_build_latest(loo):
    sys.argv = ['vindaloo', '--noninteractive', 'build', '--latest', 'test/foo']

    with chdir('tests/test_roots/simple'):
        loo.main()

    # check the parameters docker was called with
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

    # check generated Dockerfile
    with open('tests/test_roots/simple/Dockerfile', 'r') as fp:
        assert fp.read() == """FROM debian

LABEL maintainer="Test Test <test.test@firma.seznam.cz>"
LABEL description="Foo"
LABEL version="1.0.0"
"""


def test_build_latest_with_cache(loo):
    sys.argv = ['vindaloo', '--noninteractive', 'build', '--cache', '--latest', 'test/foo']

    with chdir('tests/test_roots/simple'):
        loo.main()

    # check the parameters docker was called with
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

    # check generated Dockerfile
    with open('tests/test_roots/simple/Dockerfile', 'r') as fp:
        assert fp.read() == """FROM debian

LABEL maintainer="Test Test <test.test@firma.seznam.cz>"
LABEL description="Foo"
LABEL version="1.0.0"
"""
