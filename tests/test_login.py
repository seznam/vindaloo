import sys

from utils import chdir


def test_login_ng(loo):
    # fake arguments
    sys.argv = ['vindaloo', 'kubelogin']

    with chdir('tests'):
        loo.main()

    assert loo.cmd.call_args[0][0][0] == 'bash'
    assert loo.cmd.call_args[0][0][1].endswith("kube-dex-login.sh")
