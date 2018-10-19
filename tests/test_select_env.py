import sys
from unittest import mock

from utils import chdir
from vindaloo.vindaloo import Vindaloo


def test_select_dev_ko():
    # nafakujeme parametry
    sys.argv = ['vindaloo', 'kubeenv', 'dev', 'ko']

    loo = Vindaloo()
    loo.cmd = mock.Mock()
    loo.cmd.return_value.returncode = 0

    with chdir('tests'):
        loo.main()

    assert loo.cmd.call_args[0][0] == ['kubectl', 'config', 'use-context', 'foo-dev-ko']


def test_select_dev_ng():
    # nafakujeme parametry
    sys.argv = ['vindaloo', 'kubeenv', 'dev', 'ng']

    loo = Vindaloo()
    loo.cmd = mock.Mock()
    loo.cmd.return_value.returncode = 0

    with chdir('tests'):
        loo.main()

    assert loo.cmd.call_args[0][0] == ['kubectl', 'config', 'use-context', 'foo-dev-ng']
