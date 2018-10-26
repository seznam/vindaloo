from unittest import mock

from vindaloo.vindaloo import Vindaloo


def test_cmd():
    loo = Vindaloo()
    loo.args = mock.Mock()
    loo.args.debug = False
    loo.args.dryrun = False
    res = loo.cmd(['true'])
    assert res.returncode == 0


def test_cmd_dryrun(capsys):
    loo = Vindaloo()
    loo.args = mock.Mock()
    loo.args.debug = False
    loo.args.dryrun = True
    loo.args.quiet = False
    res = loo.cmd(['kubectl', 'get', 'pod'])
    assert res.returncode == 0

    captured = capsys.readouterr()
    output = captured.out
    assert output.strip() == 'CALL:  kubectl get pod'


def test_quiet(capsys):
    loo = Vindaloo()
    loo.args = mock.Mock()
    loo.args.debug = False
    loo.args.dryrun = True
    loo.args.quiet = True
    res = loo.cmd(['kubectl', 'get', 'pod'])
    assert res.returncode == 0

    captured = capsys.readouterr()
    output = captured.out
    assert not output.strip()


@mock.patch('argparse._sys.exit')
def test_fail(mock_sys_exit, capsys):
    Vindaloo().fail('msg')

    output = capsys.readouterr().out.strip()
    assert output == 'msg'
    assert mock_sys_exit.call_args[0][0] == -1
