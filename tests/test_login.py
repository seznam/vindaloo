import sys

from utils import chdir


def test_login_ko(loo):
    # nafakujeme parametry
    sys.argv = ['vindaloo', 'kubelogin', 'ko']

    with chdir('tests'):
        loo.main()

    assert loo.cmd.call_args[0][0][0] == 'bash'
    assert loo.cmd.call_args[0][0][2] == 'ko'


def test_login_ng(loo):
    # nafakujeme parametry
    sys.argv = ['vindaloo', 'kubelogin', 'ng']

    with chdir('tests'):
        loo.main()

    assert loo.cmd.call_args[0][0][0] == 'bash'
    assert loo.cmd.call_args[0][0][2] == 'ng'
