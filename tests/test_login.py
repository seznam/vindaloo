import sys
from unittest import mock

from utils import chdir
from vindaloo.vindaloo import Vindaloo


def test_login_ko():
    # nafakujeme parametry
    sys.argv = ['vindaloo', 'kubelogin', 'ko']

    loo = Vindaloo()
    loo.cmd = mock.Mock()
    loo.cmd.return_value.returncode = 0

    with chdir('tests'):
        loo.main()

    assert loo.cmd.call_args[0][0][0] == 'bash'
    assert loo.cmd.call_args[0][0][2] == 'ko'


def test_login_ng():
    # nafakujeme parametry
    sys.argv = ['vindaloo', 'kubelogin', 'ng']

    loo = Vindaloo()
    loo.cmd = mock.Mock()
    loo.cmd.return_value.returncode = 0

    with chdir('tests'):
        loo.main()

    assert loo.cmd.call_args[0][0][0] == 'bash'
    assert loo.cmd.call_args[0][0][2] == 'ng'
