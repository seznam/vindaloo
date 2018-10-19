import sys
from unittest import mock

from utils import chdir
from vindaloo.vindaloo import Vindaloo


def test_push_all():
    # nafakujeme parametry
    sys.argv = ['vindaloo', '--noninteractive', 'push']

    loo = Vindaloo()
    loo.cmd = mock.Mock()
    loo.cmd().returncode = 0
    loo.cmd().stdout.decode().split.return_value = [
        'doc.ker.dev.dszn.cz/test/foo:1.0.0',
        'doc.ker.dev.dszn.cz/test/bar:2.0.0',
    ]

    with chdir('tests'):
        loo.main()

    # zkontrolujeme s jakymi parametry byl zavolan docker
    assert len(loo.cmd.call_args_list) == 5
    assert loo.cmd.call_args_list[3][0][0] == [
        'docker',
        'push',
        'doc.ker.dev.dszn.cz/test/foo:1.0.0',
    ]
    assert loo.cmd.call_args_list[4][0][0] == [
        'docker',
        'push',
        'doc.ker.dev.dszn.cz/test/bar:2.0.0',
    ]


def test_push_one():
    sys.argv = ['vindaloo', '--noninteractive', 'push', 'test/foo']

    loo = Vindaloo()
    loo.cmd = mock.Mock()
    loo.cmd().returncode = 0
    loo.cmd().stdout.decode().split.return_value = [
        'doc.ker.dev.dszn.cz/test/foo:1.0.0',
        'doc.ker.dev.dszn.cz/test/bar:2.0.0',
    ]

    with chdir('tests'):
        loo.main()

    # zkontrolujeme s jakymi parametry byl zavolan docker
    assert len(loo.cmd.call_args_list) == 4
    assert loo.cmd.call_args_list[3][0][0] == [
        'docker',
        'push',
        'doc.ker.dev.dszn.cz/test/foo:1.0.0',
    ]


def test_push_not_built_image():
    sys.argv = ['vindaloo', '--noninteractive', 'push', 'test/foo']

    loo = Vindaloo()
    loo.cmd = mock.Mock()
    loo.cmd().returncode = 0
    loo.cmd().stdout.decode().split.return_value = [
        'doc.ker.dev.dszn.cz/test/foo:0.0.9',  # je ubildena jina verze
        'doc.ker.dev.dszn.cz/test/bar:2.0.0',
    ]

    with chdir('tests'):
        loo.main()

    # zkontrolujeme s jakymi parametry byl zavolan docker
    assert len(loo.cmd.call_args_list) == 3
    assert loo.cmd.call_args_list[2][0][0] == [
        'docker', 'images', '--format', '{{.Repository}}:{{.Tag}}'
    ]


def test_push_latest():
    sys.argv = ['vindaloo', '--noninteractive', 'push', '--latest', 'test/foo']

    loo = Vindaloo()
    loo.cmd = mock.Mock()
    loo.cmd().returncode = 0
    loo.cmd().stdout.decode().split.return_value = [
        'doc.ker.dev.dszn.cz/test/foo:1.0.0',
        'doc.ker.dev.dszn.cz/test/bar:2.0.0',
    ]

    with chdir('tests'):
        loo.main()

    # zkontrolujeme s jakymi parametry byl zavolan docker
    assert len(loo.cmd.call_args_list) == 5
    assert loo.cmd.call_args_list[3][0][0] == [
        'docker',
        'push',
        'doc.ker.dev.dszn.cz/test/foo:1.0.0',
    ]
    assert loo.cmd.call_args_list[4][0][0] == [
        'docker',
        'push',
        'doc.ker.dev.dszn.cz/test/foo:latest',
    ]


def test_push_with_registry():
    sys.argv = ['vindaloo', '--noninteractive', 'push', '--registry', 'doc.ker', 'test/foo']

    loo = Vindaloo()
    loo.cmd = mock.Mock()
    loo.cmd().returncode = 0
    loo.cmd().stdout.decode().split.return_value = [
        'doc.ker.dev.dszn.cz/test/foo:1.0.0',
        'doc.ker.dev.dszn.cz/test/bar:2.0.0',
    ]

    with chdir('tests'):
        loo.main()

    # zkontrolujeme s jakymi parametry byl zavolan docker
    assert len(loo.cmd.call_args_list) == 5
    assert loo.cmd.call_args_list[3][0][0] == [
        'docker',
        'tag',
        'doc.ker.dev.dszn.cz/test/foo:1.0.0',
        'doc.ker/test/foo:1.0.0',
    ]
    assert loo.cmd.call_args_list[4][0][0] == [
        'docker',
        'push',
        'doc.ker/test/foo:1.0.0',
    ]
