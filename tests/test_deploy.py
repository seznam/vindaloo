import sys

from utils import chdir


def test_deploy(loo):
    # nafakujeme parametry
    sys.argv = ['vindaloo', '--noninteractive', 'deploy', 'dev']

    loo.cmd.return_value.stdout.decode.return_value.split.return_value = [
        'doc.ker.dev.dszn.cz/test/foo:1.0.0',
        'doc.ker.dev.dszn.cz/test/bar:2.0.0',
    ]

    with chdir('tests'):
        loo.main()

    # zkontrolujeme s jakymi parametry byl zavolan docker a kubectl
    assert len(loo.cmd.call_args_list) == 3
    auth_cmd = loo.cmd.call_args_list[0][0][0]
    use_context_cmd = loo.cmd.call_args_list[1][0][0]
    apply_cmd = loo.cmd.call_args_list[2][0][0][0:3]

    assert auth_cmd == [
        'kubectl',
        'auth',
        'can-i',
        'get',
        'deployment'
    ]
    assert use_context_cmd == [
        'kubectl',
        'config',
        'use-context',
        'foo-dev-ko',
    ]
    assert apply_cmd == [
        'kubectl',
        'apply',
        '-f',
    ]


def test_deploy_one_cluster(loo):
    # nafakujeme parametry
    sys.argv = ['vindaloo', '--noninteractive', 'deploy', 'dev', 'ng']

    loo.cmd.return_value.stdout.decode.return_value.split.return_value = [
        'doc.ker.dev.dszn.cz/test/foo:1.0.0',
        'doc.ker.dev.dszn.cz/test/bar:2.0.0',
    ]

    with chdir('tests'):
        loo.main()

    # zkontrolujeme s jakymi parametry byl zavolan docker a kubectl
    assert len(loo.cmd.call_args_list) == 3
    auth_cmd = loo.cmd.call_args_list[0][0][0]
    use_context_cmd = loo.cmd.call_args_list[1][0][0]
    apply_cmd = loo.cmd.call_args_list[2][0][0][0:3]

    assert auth_cmd == [
        'kubectl',
        'auth',
        'can-i',
        'get',
        'deployment'
    ]
    assert use_context_cmd == [
        'kubectl',
        'config',
        'use-context',
        'foo-dev-ng',
    ]
    assert apply_cmd == [
        'kubectl',
        'apply',
        '-f',
    ]


def test_deploy_watch(loo):
    # nafakujeme parametry
    sys.argv = ['vindaloo', '--noninteractive', 'deploy', '--watch', 'dev']

    loo.cmd.return_value.stdout.decode.return_value.split.return_value = [
        'doc.ker.dev.dszn.cz/test/foo:1.0.0',
        'doc.ker.dev.dszn.cz/test/bar:2.0.0',
    ]

    with chdir('tests'):
        loo.main()

    # zkontrolujeme s jakymi parametry byl zavolan docker a kubectl
    assert len(loo.cmd.call_args_list) == 4
    auth_cmd = loo.cmd.call_args_list[0][0][0]
    use_context_cmd = loo.cmd.call_args_list[1][0][0]
    apply_cmd = loo.cmd.call_args_list[2][0][0][0:3]
    rollout_cmd = loo.cmd.call_args_list[3][0][0]

    assert auth_cmd == [
        'kubectl',
        'auth',
        'can-i',
        'get',
        'deployment'
    ]
    assert use_context_cmd == [
        'kubectl',
        'config',
        'use-context',
        'foo-dev-ko',
    ]
    assert apply_cmd == [
        'kubectl',
        'apply',
        '-f',
    ]
    assert rollout_cmd == [
        'kubectl',
        'rollout',
        'status',
        'deployment',
        'foobar'
    ]
