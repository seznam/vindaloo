import sys

from utils import chdir


def test_push_all(loo):
    # fake arguments
    sys.argv = ['vindaloo', '--noninteractive', 'push', 'dev']

    loo.cmd.return_value.stdout.decode.return_value.split.return_value = [
        'foo-registry.com/test/foo:1.0.0',
        'foo-registry.com/test/bar:2.0.0',
    ]

    with chdir('tests/test_roots/simple'):
        loo.main()

    # check the arguments docker was called with
    assert len(loo.cmd.call_args_list) == 3
    push_cmd = loo.cmd.call_args_list[1][0][0]
    push2_cmd = loo.cmd.call_args_list[2][0][0]
    assert push_cmd == [
        'docker',
        'push',
        'foo-registry.com/test/foo:1.0.0',
    ]
    assert push2_cmd == [
        'docker',
        'push',
        'foo-registry.com/test/bar:2.0.0',
    ]


def test_push_one(loo):
    sys.argv = ['vindaloo', '--noninteractive', 'push', 'dev', 'test/foo']

    loo.cmd.return_value.stdout.decode.return_value.split.return_value = [
        'foo-registry.com/test/foo:1.0.0',
        'foo-registry.com/test/bar:2.0.0',
    ]

    with chdir('tests/test_roots/simple'):
        loo.main()

    # check the arguments docker was called with
    assert len(loo.cmd.call_args_list) == 2
    assert loo.cmd.call_args_list[1][0][0] == [
        'docker',
        'push',
        'foo-registry.com/test/foo:1.0.0',
    ]


def test_push_not_built_image(loo):
    sys.argv = ['vindaloo', '--noninteractive', 'push', 'dev', 'test/foo']

    loo.cmd.return_value.stdout.decode.return_value.split.return_value = [
        'foo-registry.com/test/foo:0.0.9',  # je ubildena jina verze
        'foo-registry.com/test/bar:2.0.0',
    ]

    with chdir('tests/test_roots/simple'):
        loo.main()

    # check the arguments docker was called with
    assert len(loo.cmd.call_args_list) == 1
    assert loo.cmd.call_args_list[0][0][0] == [
        'docker', 'images', '--format', '{{.Repository}}:{{.Tag}}'
    ]


def test_push_latest(loo):
    sys.argv = ['vindaloo', '--noninteractive', 'push', '--latest', 'dev', 'test/foo']

    loo.cmd.return_value.stdout.decode.return_value.split.return_value = [
        'foo-registry.com/test/foo:1.0.0',
        'foo-registry.com/test/bar:2.0.0',
    ]

    with chdir('tests/test_roots/simple'):
        loo.main()

    # check the arguments docker was called with
    assert len(loo.cmd.call_args_list) == 3
    push_cmd = loo.cmd.call_args_list[1][0][0]
    push2_cmd = loo.cmd.call_args_list[2][0][0]

    assert push_cmd == [
        'docker',
        'push',
        'foo-registry.com/test/foo:1.0.0',
    ]
    assert push2_cmd == [
        'docker',
        'push',
        'foo-registry.com/test/foo:latest',
    ]


def test_push_with_registry(loo):
    sys.argv = ['vindaloo', '--noninteractive', 'push', '--registry', 'foo-prog-registry.com', 'dev', 'test/foo']

    loo.cmd.return_value.stdout.decode.return_value.split.return_value = [
        'foo-registry.com/test/foo:1.0.0',
        'foo-registry.com/test/bar:2.0.0',
    ]

    with chdir('tests/test_roots/simple'):
        loo.main()

    # check the arguments docker was called with
    assert len(loo.cmd.call_args_list) == 3
    tag_cmd = loo.cmd.call_args_list[1][0][0]
    push_cmd = loo.cmd.call_args_list[2][0][0]

    assert tag_cmd == [
        'docker',
        'tag',
        'foo-registry.com/test/foo:1.0.0',
        'foo-prog-registry.com/test/foo:1.0.0',
    ]
    assert push_cmd == [
        'docker',
        'push',
        'foo-prog-registry.com/test/foo:1.0.0',
    ]
