import sys
from unittest import mock

from utils import chdir
from vindaloo.vindaloo import Vindaloo


def test_build_all():
    # nafakujeme parametry
    sys.argv = ['vindaloo', '--noninteractive', 'build']

    loo = Vindaloo()
    loo.cmd = mock.Mock()
    loo.cmd.return_value.returncode = 0

    with chdir('tests'):
        loo.main()

    # zkontrolujeme s jakymi parametry byl zavolan docker
    assert loo.cmd.call_args_list == [
        (([
            'docker',
            'build',
            '--no-cache',
            '-t', 'doc.ker.dev.dszn.cz/test/foo:1.0.0',
            '-f', 'Dockerfile',
            '.'
        ],),),
        (([
            'docker',
            'build',
            '--no-cache',
            '-t', 'doc.ker.dev.dszn.cz/test/bar:2.0.0',
            '-f', 'Dockerfile',
            '.'
        ],),),
    ]

    # zkontrolujeme vygenerovany Dockerfile
    with open('tests/Dockerfile', 'r') as fp:
        lines = [line.strip() for line in fp]
        assert lines[0] == 'LABEL maintainer="Test Test <test.test@firma.seznam.cz>"'
        assert lines[1] == 'LABEL description="Bar"'
        assert lines[2] == 'LABEL version="2.0.0"'


def test_build_one():
    sys.argv = ['vindaloo', '--noninteractive', 'build', 'test/foo']

    loo = Vindaloo()
    loo.cmd = mock.Mock()
    loo.cmd.return_value.returncode = 0

    with chdir('tests'):
        loo.main()

    # zkontrolujeme s jakymi parametry byl zavolan docker
    assert loo.cmd.call_args_list == [
        (([
            'docker',
            'build',
            '--no-cache',
            '-t', 'doc.ker.dev.dszn.cz/test/foo:1.0.0',
            '-f', 'Dockerfile',
            '.'
        ],),),
    ]

    # zkontrolujeme vygenerovany Dockerfile
    with open('tests/Dockerfile', 'r') as fp:
        lines = [line.strip() for line in fp]
        assert lines[0] == 'FROM debian'
        assert lines[2] == 'LABEL maintainer="Test Test <test.test@firma.seznam.cz>"'
        assert lines[3] == 'LABEL description="Foo"'
        assert lines[4] == 'LABEL version="1.0.0"'


def test_build_latest():
    sys.argv = ['vindaloo', '--noninteractive', 'build', '--latest', 'test/foo']

    loo = Vindaloo()
    loo.cmd = mock.Mock()
    loo.cmd.return_value.returncode = 0

    with chdir('tests'):
        loo.main()

    # zkontrolujeme s jakymi parametry byl zavolan docker
    assert loo.cmd.call_args_list == [
        (([
            'docker',
            'build',
            '--no-cache',
            '-t', 'doc.ker.dev.dszn.cz/test/foo:1.0.0',
            '-t', 'doc.ker.dev.dszn.cz/test/foo:latest',
            '-f', 'Dockerfile',
            '.'
        ],),),
    ]

    # zkontrolujeme vygenerovany Dockerfile
    with open('tests/Dockerfile', 'r') as fp:
        lines = [line.strip() for line in fp]
        assert lines[0] == 'FROM debian'
        assert lines[2] == 'LABEL maintainer="Test Test <test.test@firma.seznam.cz>"'
        assert lines[3] == 'LABEL description="Foo"'
        assert lines[4] == 'LABEL version="1.0.0"'
