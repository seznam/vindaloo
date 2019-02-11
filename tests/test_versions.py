import sys
from unittest import mock

from utils import chdir
from vindaloo.vindaloo import Vindaloo


def test_versions_match(capsys):
    # fake arguments
    sys.argv = ['vindaloo', 'versions']

    calls = [mock.Mock() for _ in range(5)]
    for call in calls:
        call.returncode = 0
    calls[2].stdout = b'doc.ker.dev.dszn.cz/test/foo:1.0.0 doc.ker.dev.dszn.cz/test/bar:2.0.0'  # ko
    calls[4].stdout = b'doc.ker.dev.dszn.cz/test/foo:1.0.0 doc.ker.dev.dszn.cz/test/bar:2.0.0'  # ng

    loo = Vindaloo()
    loo.cmd = mock.Mock()
    loo.cmd.side_effect = calls

    with chdir('tests'):
        loo.main()

    # check the arguments kubectl was called with
    assert len(loo.cmd.call_args_list) == 5

    assert loo.cmd.call_args_list[0][0][0] == [
        'kubectl',
        'auth',
        'can-i',
        'get',
        'deployment'
    ]
    assert loo.cmd.call_args_list[1][0][0][:3] == [
        'kubectl',
        'config',
        'use-context',
    ]
    assert loo.cmd.call_args_list[1][0][0][3] in ('foo-dev-ko', 'foo-dev-ng')  # nezname poradi
    assert loo.cmd.call_args_list[2][0][0] == [
        'kubectl',
        'get',
        'deployment',
        'foobar',
        '-o=jsonpath=\'{$.spec.template.spec.containers[*].image}\''
    ]
    assert loo.cmd.call_args_list[3][0][0][:3] == [
        'kubectl',
        'config',
        'use-context',
    ]
    assert loo.cmd.call_args_list[3][0][0][3] in ('foo-dev-ko', 'foo-dev-ng')  # nezname poradi
    assert loo.cmd.call_args_list[4][0][0] == [
        'kubectl',
        'get',
        'deployment',
        'foobar',
        '-o=jsonpath=\'{$.spec.template.spec.containers[*].image}\''
    ]

    output = capsys.readouterr().out.strip()

    assert '[DIFFERS]' not in output
    assert 'test/foo' in output
    assert 'test/bar' in output


def test_versions_not_match(capsys):
    # fake arguments
    sys.argv = ['vindaloo', 'versions']

    def x(*args, **kwargs):
        print(args, kwargs)
        z = mock.Mock()
        z.returncode = 0
        return z

    calls = [mock.Mock() for _ in range(5)]
    for call in calls:
        call.returncode = 0
    calls[2].stdout = b'doc.ker.dev.dszn.cz/test/foo:1.0.0 doc.ker.dev.dszn.cz/test/bar:2.0.0'  # ko
    calls[4].stdout = b'doc.ker.dev.dszn.cz/test/foo:0.0.9 doc.ker.dev.dszn.cz/test/bar:2.0.0'  # ng DIFFERS

    loo = Vindaloo()
    loo.cmd = mock.Mock()
    loo.cmd.side_effect = calls

    with chdir('tests'):
        loo.main()

    # check the arguments kubectl was called with
    assert len(loo.cmd.call_args_list) == 5

    assert loo.cmd.call_args_list[0][0][0] == [
        'kubectl',
        'auth',
        'can-i',
        'get',
        'deployment'
    ]
    assert loo.cmd.call_args_list[1][0][0][:3] == [
        'kubectl',
        'config',
        'use-context',
    ]
    assert loo.cmd.call_args_list[1][0][0][3] in ('foo-dev-ko', 'foo-dev-ng')  # nezname poradi
    assert loo.cmd.call_args_list[2][0][0] == [
        'kubectl',
        'get',
        'deployment',
        'foobar',
        '-o=jsonpath=\'{$.spec.template.spec.containers[*].image}\''
    ]
    assert loo.cmd.call_args_list[3][0][0][:3] == [
        'kubectl',
        'config',
        'use-context',
    ]
    assert loo.cmd.call_args_list[3][0][0][3] in ('foo-dev-ko', 'foo-dev-ng')  # nezname poradi
    assert loo.cmd.call_args_list[4][0][0] == [
        'kubectl',
        'get',
        'deployment',
        'foobar',
        '-o=jsonpath=\'{$.spec.template.spec.containers[*].image}\''
    ]

    output = capsys.readouterr().out.strip()

    assert '[DIFFERS]' in output
    assert 'test/foo' in output
    assert 'test/bar' in output
