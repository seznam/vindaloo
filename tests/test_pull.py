import sys
from unittest import mock

from utils import chdir
from vindaloo.vindaloo import Vindaloo


def test_pull_all():
    # nafakujeme parametry
    sys.argv = ['vindaloo', '--noninteractive', 'pull']

    loo = Vindaloo()
    loo.cmd = mock.Mock()
    loo.cmd().returncode = 0
    loo.cmd().stdout.decode().split.return_value = []

    with chdir('tests'):
        loo.main()

    # zkontrolujeme s jakymi parametry byl zavolan docker
    assert len(loo.cmd.call_args_list) == 5
    assert loo.cmd.call_args_list[3][0][0] == [
        'docker',
        'pull',
        'doc.ker.dev.dszn.cz/test/foo:1.0.0',
    ]
    assert loo.cmd.call_args_list[4][0][0] == [
        'docker',
        'pull',
        'doc.ker.dev.dszn.cz/test/bar:2.0.0',
    ]


def test_pull_one():
    sys.argv = ['vindaloo', '--noninteractive', 'pull', 'test/foo']

    loo = Vindaloo()
    loo.cmd = mock.Mock()
    loo.cmd().returncode = 0
    loo.cmd().stdout.decode().split.return_value = []

    with chdir('tests'):
        loo.main()

    # zkontrolujeme s jakymi parametry byl zavolan docker
    assert len(loo.cmd.call_args_list) == 4
    assert loo.cmd.call_args_list[3][0][0] == [
        'docker',
        'pull',
        'doc.ker.dev.dszn.cz/test/foo:1.0.0',
    ]


def test_pull_already_present():
    sys.argv = ['vindaloo', '--noninteractive', 'pull', 'test/foo']

    loo = Vindaloo()
    loo.cmd = mock.Mock()
    loo.cmd().returncode = 0
    loo.cmd().stdout.decode().split.return_value = [
        'doc.ker.dev.dszn.cz/test/foo:1.0.0',
    ]

    with chdir('tests'):
        loo.main()

    # zkontrolujeme s jakymi parametry byl zavolan docker
    assert len(loo.cmd.call_args_list) == 3
    assert loo.cmd.call_args_list[2][0][0] == [
        'docker', 'images', '--format', '{{.Repository}}:{{.Tag}}'
    ]
