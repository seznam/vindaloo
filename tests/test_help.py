import sys
from unittest import mock

import pytest

from utils import chdir
from vindaloo.vindaloo import Vindaloo

ALL_CMDS_STRING = 'build,pull,push,kubeenv,version,versions,deploy,deploy-dir,build-push-deploy'


@mock.patch('argparse._sys.exit')
def test_help(mock_sys_exit, capsys):
    sys.argv = ['vindaloo', '-h']

    with chdir('tests/test_roots/simple'):
        Vindaloo().main()

    captured = capsys.readouterr()
    output = captured.out

    assert mock_sys_exit.call_args[0][0] == 0
    assert 'usage' in output
    assert ALL_CMDS_STRING in output


@mock.patch('argparse._sys.exit')
def test_help_build(mock_sys_exit, capsys):
    sys.argv = ['vindaloo', 'build', '-h']

    mock_sys_exit.side_effect = Exception()

    with chdir('tests/test_roots/simple'):
        with pytest.raises(Exception):
            Vindaloo().main()

    captured = capsys.readouterr()
    output = captured.out

    assert 'usage' in output
    assert '--latest' in output
    assert ALL_CMDS_STRING not in output
