import json
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
    calls[2].stdout = b'foo-registry.com/test/foo:1.0.0 foo-registry.com/test/bar:2.0.0'  # cluster1
    calls[4].stdout = b'foo-registry.com/test/foo:1.0.0 foo-registry.com/test/bar:2.0.0'  # cluster2

    loo = Vindaloo()
    loo.cmd = mock.Mock()
    loo.cmd.side_effect = calls

    with chdir('tests/test_roots/simple'):
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
    assert loo.cmd.call_args_list[1][0][0][3] in ('foo-dev:cluster1', 'foo-dev:cluster2')  # nezname poradi
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
    assert loo.cmd.call_args_list[3][0][0][3] in ('foo-dev:cluster1', 'foo-dev:cluster2')  # nezname poradi
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
    calls[2].stdout = b'foo-registry.com/test/foo:1.0.0 foo-registry.com/test/bar:2.0.0'  # cluster1
    calls[4].stdout = b'foo-registry.com/test/foo:0.0.9 foo-registry.com/test/bar:2.0.0'  # cluster2 DIFFERS

    loo = Vindaloo()
    loo.cmd = mock.Mock()
    loo.cmd.side_effect = calls

    with chdir('tests/test_roots/simple'):
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
    assert loo.cmd.call_args_list[1][0][0][3] in ('foo-dev:cluster1', 'foo-dev:cluster2')  # unknown order
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
    assert loo.cmd.call_args_list[3][0][0][3] in ('foo-dev:cluster1', 'foo-dev:cluster2')  # unknown order
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


def test_versions_json(capsys):
    # fake arguments
    sys.argv = ['vindaloo', 'versions', '--json']

    def x(*args, **kwargs):
        print(args, kwargs)
        z = mock.Mock()
        z.returncode = 0
        return z

    calls = [mock.Mock() for _ in range(5)]
    for call in calls:
        call.returncode = 0
    calls[2].stdout = b'foo-registry.com/test/foo:1.0.0 foo-registry.com/test/bar:2.0.0'  # c1
    calls[4].stdout = b'foo-registry.com/test/foo:0.0.9 foo-registry.com/test/bar:2.0.0'  # c2 DIFFERS

    loo = Vindaloo()
    loo.cmd = mock.Mock()
    loo.cmd.side_effect = calls

    with chdir('tests/test_roots/simple'):
        loo.main()

    # check the arguments kubectl was called with
    assert len(loo.cmd.call_args_list) == 5

    output = capsys.readouterr().out.strip()
    data = json.loads(output)
    assert data
    assert data['dev']['test/foo']['local'] == '1.0.0'
    assert data['dev']['test/bar']['local'] == '2.0.0'

    assert data['dev']['test/bar']['remote']['cluster1'] == '2.0.0'

    # py 3.5 has no fixed dict ordering, so we don't know if c1 or c2 will be first
    assert data['dev']['test/foo']['remote']['cluster1'] in ('1.0.0', '0.0.9')
    assert data['dev']['test/foo']['remote']['cluster2'] in ('1.0.0', '0.0.9')
