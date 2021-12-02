import sys
from unittest import mock

from utils import chdir


def test_build_all(loo):
    # fake parameters
    sys.argv = ['vindaloo', '--noninteractive', 'build', 'dev']

    rev_parse_mock = mock.Mock()
    rev_parse_mock.stdout = b'd6ee34ae'
    build_mock = mock.Mock()
    build_mock.returncode = 0
    loo.cmd.side_effect = [rev_parse_mock, build_mock, build_mock]

    with chdir('tests/test_roots/simple'):
        loo.main()

    # check the parameters docker was called with
    rev_parse_cmd = loo.cmd.call_args_list[0][0][0]
    build_cmd = loo.cmd.call_args_list[1][0][0]
    build_cmd2 = loo.cmd.call_args_list[2][0][0]

    assert rev_parse_cmd == [
        'git',
        'rev-parse',
        '--short=8',
        'HEAD'
    ]
    assert build_cmd == [
        'docker',
        'build',
        '-t', 'foo-registry.com/test/foo:d6ee34ae-dev',
        '--no-cache',
        '-f', 'Dockerfile',
        '.'
    ]
    assert build_cmd2 == [
        'docker',
        'build',
        '-t', 'foo-registry.com/test/bar:2.0.0',
        '--no-cache',
        '-f', 'Dockerfile',
        '.'
    ]

    # check generated Dockerfile
    with open('tests/test_roots/simple/Dockerfile', 'r') as fp:
        assert fp.read() == """LABEL maintainer="Test Test <test.test@firma.seznam.cz>"
LABEL description="Bar"
LABEL version="2.0.0"
"""


def test_build_one(loo):
    sys.argv = ['vindaloo', '--noninteractive', 'build', 'dev', 'test/foo']

    rev_parse_mock = mock.Mock()
    rev_parse_mock.stdout = b'd6ee34ae'
    build_mock = mock.Mock()
    build_mock.returncode = 0
    loo.cmd.side_effect = [rev_parse_mock, build_mock]

    with chdir('tests/test_roots/simple'):
        loo.main()

    # check the parameters docker was called with
    rev_parse_cmd = loo.cmd.call_args_list[0][0][0]
    build_cmd = loo.cmd.call_args_list[1][0][0]

    assert rev_parse_cmd == [
        'git',
        'rev-parse',
        '--short=8',
        'HEAD'
    ]
    assert build_cmd == [
        'docker',
        'build',
        '-t', 'foo-registry.com/test/foo:d6ee34ae-dev',
        '--no-cache',
        '-f', 'Dockerfile',
        '.'
    ]

    # check generated Dockerfile
    with open('tests/test_roots/simple/Dockerfile', 'r') as fp:
        assert fp.read() == """FROM debian

LABEL maintainer="Test Test <test.test@firma.seznam.cz>"
LABEL description="Foo"
LABEL version="d6ee34ae-dev"
"""


def test_build_latest(loo):
    sys.argv = ['vindaloo', '--noninteractive', 'build', '--latest', 'dev', 'test/foo']

    rev_parse_mock = mock.Mock()
    rev_parse_mock.stdout = b'd6ee34ae'
    build_mock = mock.Mock()
    build_mock.returncode = 0
    loo.cmd.side_effect = [rev_parse_mock, build_mock]

    with chdir('tests/test_roots/simple'):
        loo.main()

    # check the parameters docker was called with
    rev_parse_cmd = loo.cmd.call_args_list[0][0][0]
    build_cmd = loo.cmd.call_args_list[1][0][0]

    assert rev_parse_cmd == [
        'git',
        'rev-parse',
        '--short=8',
        'HEAD'
    ]
    assert build_cmd == [
        'docker',
        'build',
        '-t', 'foo-registry.com/test/foo:d6ee34ae-dev',
        '--no-cache',
        '-t', 'foo-registry.com/test/foo:latest',
        '-f', 'Dockerfile',
        '.'
    ]

    # check generated Dockerfile
    with open('tests/test_roots/simple/Dockerfile', 'r') as fp:
        assert fp.read() == """FROM debian

LABEL maintainer="Test Test <test.test@firma.seznam.cz>"
LABEL description="Foo"
LABEL version="d6ee34ae-dev"
"""


def test_build_latest_with_cache(loo):
    sys.argv = ['vindaloo', '--noninteractive', 'build', '--cache', '--latest', 'dev', 'test/foo']

    rev_parse_mock = mock.Mock()
    rev_parse_mock.stdout = b'd6ee34ae'
    build_mock = mock.Mock()
    build_mock.returncode = 0
    loo.cmd.side_effect = [rev_parse_mock, build_mock]

    with chdir('tests/test_roots/simple'):
        loo.main()

    # check the parameters docker was called with
    rev_parse_cmd = loo.cmd.call_args_list[0][0][0]
    build_cmd = loo.cmd.call_args_list[1][0][0]

    assert rev_parse_cmd == [
        'git',
        'rev-parse',
        '--short=8',
        'HEAD'
    ]
    assert build_cmd == [
        'docker',
        'build',
        '-t', 'foo-registry.com/test/foo:d6ee34ae-dev',
        '-t', 'foo-registry.com/test/foo:latest',
        '-f', 'Dockerfile',
        '.'
    ]

    # check generated Dockerfile
    with open('tests/test_roots/simple/Dockerfile', 'r') as fp:
        assert fp.read() == """FROM debian

LABEL maintainer="Test Test <test.test@firma.seznam.cz>"
LABEL description="Foo"
LABEL version="d6ee34ae-dev"
"""
