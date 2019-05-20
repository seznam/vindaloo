import sys

from utils import chdir


def test_select_dev_ko(loo):
    # fake arguments
    sys.argv = ['vindaloo', 'kubeenv', 'dev', 'ko']

    with chdir('tests/test_roots/simple'):
        loo.main()

    assert loo.cmd.call_args[0][0] == ['kubectl', 'config', 'use-context', 'foo-dev-ko']


def test_select_dev_ng(loo):
    # fake arguments
    sys.argv = ['vindaloo', 'kubeenv', 'dev', 'ng']

    with chdir('tests/test_roots/simple'):
        loo.main()

    assert loo.cmd.call_args[0][0] == ['kubectl', 'config', 'use-context', 'foo-dev-ng']
