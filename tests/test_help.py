import sys
from unittest import mock

import pytest

from utils import chdir
from vindaloo.vindaloo import Vindaloo


@mock.patch('argparse._sys.exit')
def test_help(mock_sys_exit, capsys):
    sys.argv = ['vindaloo', '-h']

    with chdir('tests'):
        Vindaloo().main()

    captured = capsys.readouterr()
    output = captured.out

    assert mock_sys_exit.call_args[0][0] == 0
    assert 'usage' in output
    assert 'build,pull,push,kubeenv,versions,kubelogin,deploy,build-push-deploy' in output


@mock.patch('argparse._sys.exit')
def test_help_build(mock_sys_exit, capsys):
    sys.argv = ['vindaloo', 'build', '-h']

    mock_sys_exit.side_effect = Exception()

    with chdir('tests'):
        with pytest.raises(Exception):
            Vindaloo().main()

    captured = capsys.readouterr()
    output = captured.out

    assert 'usage' in output
    assert '--latest' in output
    assert 'build,pull,push,kubeenv,versions,kubelogin,deploy,build-push-deploy' not in output
