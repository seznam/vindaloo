import sys

from utils import chdir


def test_pull_all(loo):
    # fake arguments
    sys.argv = ['vindaloo', '--noninteractive', 'pull', 'dev']

    loo.cmd.return_value.stdout.decode.return_value.split.return_value = []

    with chdir('tests/test_roots/simple'):
        loo.main()

    # check the arguments docker was called with
    assert len(loo.cmd.call_args_list) == 3
    pull_cmd = loo.cmd.call_args_list[1][0][0]
    pull2_cmd = loo.cmd.call_args_list[2][0][0]

    assert pull_cmd == [
        'docker',
        'pull',
        'foo-registry.com/test/foo:1.0.0',
    ]
    assert pull2_cmd == [
        'docker',
        'pull',
        'foo-registry.com/test/bar:2.0.0',
    ]


def test_pull_one(loo):
    sys.argv = ['vindaloo', '--noninteractive', 'pull', 'dev', 'test/foo']

    loo.cmd.return_value.stdout.decode.return_value.split.return_value = []

    with chdir('tests/test_roots/simple'):
        loo.main()

    # check the arguments docker was called with
    assert len(loo.cmd.call_args_list) == 2
    assert loo.cmd.call_args_list[1][0][0] == [
        'docker',
        'pull',
        'foo-registry.com/test/foo:1.0.0',
    ]


def test_pull_already_present(loo):
    sys.argv = ['vindaloo', '--noninteractive', 'pull', 'dev', 'test/foo']

    loo.cmd.return_value.stdout.decode.return_value.split.return_value = [
        'foo-registry.com/test/foo:1.0.0',
    ]

    with chdir('tests/test_roots/simple'):
        loo.main()

    # check the arguments docker was called with
    assert len(loo.cmd.call_args_list) == 1
    assert loo.cmd.call_args_list[0][0][0] == [
        'docker', 'images', '--format', '{{.Repository}}:{{.Tag}}'
    ]
