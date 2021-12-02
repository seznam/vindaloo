import sys
from unittest import mock

from utils import chdir


def test_pull_all(loo):
    # fake arguments
    sys.argv = ['vindaloo', '--noninteractive', 'pull', 'dev']

    rev_parse_mock = mock.Mock()
    rev_parse_mock.stdout = b'd6ee34ae'

    images_mock = mock.Mock()
    images_mock.stdout.decode.return_value.split.return_value = []

    pull_mock = mock.Mock()
    pull_mock.returncode = 0

    loo.cmd.side_effect = [rev_parse_mock, images_mock, pull_mock, pull_mock]

    with chdir('tests/test_roots/simple'):
        loo.main()

    # check the arguments docker was called with
    assert len(loo.cmd.call_args_list) == 4
    pull_cmd = loo.cmd.call_args_list[2][0][0]
    pull2_cmd = loo.cmd.call_args_list[3][0][0]

    assert pull_cmd == [
        'docker',
        'pull',
        'foo-registry.com/test/foo:d6ee34ae-dev',
    ]
    assert pull2_cmd == [
        'docker',
        'pull',
        'foo-registry.com/test/bar:2.0.0',
    ]


def test_pull_one(loo):
    sys.argv = ['vindaloo', '--noninteractive', 'pull', 'dev', 'test/foo']

    rev_parse_mock = mock.Mock()
    rev_parse_mock.stdout = b'd6ee34ae'

    images_mock = mock.Mock()
    images_mock.stdout.decode.return_value.split.return_value = []

    pull_mock = mock.Mock()
    pull_mock.returncode = 0

    loo.cmd.side_effect = [rev_parse_mock, images_mock, pull_mock]

    with chdir('tests/test_roots/simple'):
        loo.main()

    # check the arguments docker was called with
    assert len(loo.cmd.call_args_list) == 3
    assert loo.cmd.call_args_list[2][0][0] == [
        'docker',
        'pull',
        'foo-registry.com/test/foo:d6ee34ae-dev',
    ]


def test_pull_already_present(loo):
    sys.argv = ['vindaloo', '--noninteractive', 'pull', 'dev', 'test/foo']

    rev_parse_mock = mock.Mock()
    rev_parse_mock.stdout = b'd6ee34ae'

    images_mock = mock.Mock()
    images_mock.stdout.decode.return_value.split.return_value = [
        'foo-registry.com/test/foo:d6ee34ae-dev',
    ]

    loo.cmd.side_effect = [rev_parse_mock, images_mock]

    with chdir('tests/test_roots/simple'):
        loo.main()

    # check the arguments docker was called with
    assert len(loo.cmd.call_args_list) == 2
    assert loo.cmd.call_args_list[1][0][0] == [
        'docker', 'images', '--format', '{{.Repository}}:{{.Tag}}'
    ]
