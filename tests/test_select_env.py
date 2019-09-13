import sys

from utils import chdir


def test_select_dev_cluster1(loo):
    # fake arguments
    sys.argv = ['vindaloo', 'kubeenv', 'dev', 'c1']

    with chdir('tests/test_roots/simple'):
        loo.main()

    assert loo.cmd.call_args[0][0] == ['kubectl', 'config', 'use-context', 'foo-dev:cluster1']


def test_select_dev_cluster2(loo):
    # fake arguments
    sys.argv = ['vindaloo', 'kubeenv', 'dev', 'c2']

    with chdir('tests/test_roots/simple'):
        loo.main()

    assert loo.cmd.call_args[0][0] == ['kubectl', 'config', 'use-context', 'foo-dev:cluster2']
