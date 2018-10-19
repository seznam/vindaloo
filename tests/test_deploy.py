import sys
from unittest import mock

from utils import chdir
from vindaloo.vindaloo import Vindaloo


def test_deploy():
    # nafakujeme parametry
    sys.argv = ['vindaloo', '--noninteractive', 'deploy', 'dev']

    loo = Vindaloo()
    loo.cmd = mock.Mock()
    loo.cmd().returncode = 0
    loo.cmd().stdout.decode().split.return_value = [
        'doc.ker.dev.dszn.cz/test/foo:1.0.0',
        'doc.ker.dev.dszn.cz/test/bar:2.0.0',
    ]

    with chdir('tests'):
        loo.main()

    # zkontrolujeme s jakymi parametry byl zavolan docker a kubectl
    assert len(loo.cmd.call_args_list) == 5
    assert loo.cmd.call_args_list[2][0][0] == [
        'kubectl',
        'auth',
        'can-i',
        'get',
        'deployment'
    ]
    assert loo.cmd.call_args_list[3][0][0] == [
        'kubectl',
        'config',
        'use-context',
        'foo-dev-ko',
    ]
    assert loo.cmd.call_args_list[4][0][0][0:3] == [
        'kubectl',
        'apply',
        '-f',
    ]


def test_deploy_one_cluster():
    # nafakujeme parametry
    sys.argv = ['vindaloo', '--noninteractive', 'deploy', 'dev', 'ng']

    loo = Vindaloo()
    loo.cmd = mock.Mock()
    loo.cmd().returncode = 0
    loo.cmd().stdout.decode().split.return_value = [
        'doc.ker.dev.dszn.cz/test/foo:1.0.0',
        'doc.ker.dev.dszn.cz/test/bar:2.0.0',
    ]

    with chdir('tests'):
        loo.main()

    # zkontrolujeme s jakymi parametry byl zavolan docker a kubectl
    assert len(loo.cmd.call_args_list) == 5
    assert loo.cmd.call_args_list[2][0][0] == [
        'kubectl',
        'auth',
        'can-i',
        'get',
        'deployment'
    ]
    assert loo.cmd.call_args_list[3][0][0] == [
        'kubectl',
        'config',
        'use-context',
        'foo-dev-ng',
    ]
    assert loo.cmd.call_args_list[4][0][0][0:3] == [
        'kubectl',
        'apply',
        '-f',
    ]
