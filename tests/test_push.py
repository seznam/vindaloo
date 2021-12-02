import sys
from unittest import mock

from utils import chdir


def test_push_all(loo):
    # fake arguments
    sys.argv = ['vindaloo', '--noninteractive', 'push', 'dev']

    rev_parse_mock = mock.Mock()
    rev_parse_mock.stdout = b'd6ee34ae'

    images_mock = mock.Mock()
    images_mock.stdout.decode.return_value.split.return_value = [
        'foo-registry.com/test/foo:d6ee34ae-dev',
        'foo-registry.com/test/bar:2.0.0',
    ]

    push_mock = mock.Mock()
    push_mock.returncode = 0

    loo.cmd.side_effect = [rev_parse_mock, images_mock, push_mock, push_mock]

    with chdir('tests/test_roots/simple'):
        loo.main()

    # check the arguments docker was called with
    assert len(loo.cmd.call_args_list) == 4
    push_cmd = loo.cmd.call_args_list[2][0][0]
    push2_cmd = loo.cmd.call_args_list[3][0][0]
    assert push_cmd == [
        'docker',
        'push',
        'foo-registry.com/test/foo:d6ee34ae-dev',
    ]
    assert push2_cmd == [
        'docker',
        'push',
        'foo-registry.com/test/bar:2.0.0',
    ]


def test_push_one(loo):
    sys.argv = ['vindaloo', '--noninteractive', 'push', 'dev', 'test/foo']

    rev_parse_mock = mock.Mock()
    rev_parse_mock.stdout = b'd6ee34ae'

    images_mock = mock.Mock()
    images_mock.stdout.decode.return_value.split.return_value = [
        'foo-registry.com/test/foo:d6ee34ae-dev',
        'foo-registry.com/test/bar:2.0.0',
    ]

    push_mock = mock.Mock()
    push_mock.returncode = 0

    loo.cmd.side_effect = [rev_parse_mock, images_mock, push_mock]

    with chdir('tests/test_roots/simple'):
        loo.main()

    # check the arguments docker was called with
    assert len(loo.cmd.call_args_list) == 3
    assert loo.cmd.call_args_list[2][0][0] == [
        'docker',
        'push',
        'foo-registry.com/test/foo:d6ee34ae-dev',
    ]


def test_push_not_built_image(loo):
    sys.argv = ['vindaloo', '--noninteractive', 'push', 'dev', 'test/foo']

    rev_parse_mock = mock.Mock()
    rev_parse_mock.stdout = b'd6ee34ae'

    images_mock = mock.Mock()
    images_mock.stdout.decode.return_value.split.return_value = [
        'foo-registry.com/test/foo:0.0.9',  # je ubildena jina verze
        'foo-registry.com/test/bar:2.0.0',
    ]

    loo.cmd.side_effect = [rev_parse_mock, images_mock]

    with chdir('tests/test_roots/simple'):
        loo.main()

    # check the arguments docker was called with
    assert len(loo.cmd.call_args_list) == 2
    assert loo.cmd.call_args_list[0][0][0] == [
        'git', 'rev-parse', '--short=8', 'HEAD'
    ]
    assert loo.cmd.call_args_list[1][0][0] == [
        'docker', 'images', '--format', '{{.Repository}}:{{.Tag}}'
    ]


def test_push_latest(loo):
    sys.argv = ['vindaloo', '--noninteractive', 'push', '--latest', 'dev', 'test/foo']

    rev_parse_mock = mock.Mock()
    rev_parse_mock.stdout = b'd6ee34ae'

    images_mock = mock.Mock()
    images_mock.stdout.decode.return_value.split.return_value = [
        'foo-registry.com/test/foo:d6ee34ae-dev',
        'foo-registry.com/test/bar:2.0.0',
    ]

    push_mock = mock.Mock()
    push_mock.returncode = 0

    loo.cmd.side_effect = [rev_parse_mock, images_mock, push_mock, push_mock]

    with chdir('tests/test_roots/simple'):
        loo.main()

    # check the arguments docker was called with
    assert len(loo.cmd.call_args_list) == 4
    push_cmd = loo.cmd.call_args_list[2][0][0]
    push2_cmd = loo.cmd.call_args_list[3][0][0]

    assert push_cmd == [
        'docker',
        'push',
        'foo-registry.com/test/foo:d6ee34ae-dev',
    ]
    assert push2_cmd == [
        'docker',
        'push',
        'foo-registry.com/test/foo:latest',
    ]


def test_push_with_registry(loo):
    sys.argv = ['vindaloo', '--noninteractive', 'push', '--registry', 'foo-prog-registry.com', 'dev', 'test/foo']

    rev_parse_mock = mock.Mock()
    rev_parse_mock.stdout = b'd6ee34ae'

    images_mock = mock.Mock()
    images_mock.stdout.decode.return_value.split.return_value = [
        'foo-registry.com/test/foo:d6ee34ae-dev',
        'foo-registry.com/test/bar:2.0.0',
    ]

    tag_mock = mock.Mock()
    tag_mock.returncode = 0

    push_mock = mock.Mock()
    push_mock.returncode = 0

    loo.cmd.side_effect = [rev_parse_mock, images_mock, tag_mock, push_mock]

    with chdir('tests/test_roots/simple'):
        loo.main()

    # check the arguments docker was called with
    assert len(loo.cmd.call_args_list) == 4
    tag_cmd = loo.cmd.call_args_list[2][0][0]
    push_cmd = loo.cmd.call_args_list[3][0][0]

    assert tag_cmd == [
        'docker',
        'tag',
        'foo-registry.com/test/foo:d6ee34ae-dev',
        'foo-prog-registry.com/test/foo:d6ee34ae-dev',
    ]
    assert push_cmd == [
        'docker',
        'push',
        'foo-prog-registry.com/test/foo:d6ee34ae-dev',
    ]
