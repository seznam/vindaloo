import json
import os
import sys

import vindaloo
from utils import chdir


def test_deploy(loo):
    # fake arguments
    sys.argv = ['vindaloo', '--noninteractive', 'deploy', 'dev', 'cluster1']

    loo.cmd.return_value.stdout.decode.return_value.split.return_value = [
        'foo-registry.com/test/foo:1.0.0',
        'foo-registry.com/test/bar:2.0.0',
    ]

    with chdir('tests/test_roots/simple'):
        loo.main()

    assert vindaloo.app.args.cluster == 'cluster1'

    # check arguments docker and kubectl was called with
    assert len(loo.cmd.call_args_list) == 3
    auth_cmd = loo.cmd.call_args_list[0][0][0]
    use_context_cmd = loo.cmd.call_args_list[1][0][0]
    apply_cmd = loo.cmd.call_args_list[2][0][0][0:3]

    assert auth_cmd == [
        'kubectl',
        'auth',
        'can-i',
        'get',
        'deployment'
    ]
    assert use_context_cmd == [
        'kubectl',
        'config',
        'use-context',
        'foo-dev:cluster1',
    ]
    assert apply_cmd == [
        'kubectl',
        'apply',
        '-f',
    ]


def test_deploy_one_cluster(loo):
    # fake arguments
    sys.argv = ['vindaloo', '--noninteractive', 'deploy', 'dev', 'cluster2']

    loo.cmd.return_value.stdout.decode.return_value.split.return_value = [
        'foo-registry.com/test/foo:1.0.0',
        'foo-registry.com/test/bar:2.0.0',
    ]

    with chdir('tests/test_roots/simple'):
        loo.main()

    # check arguments docker and kubectl was called with
    assert len(loo.cmd.call_args_list) == 3
    auth_cmd = loo.cmd.call_args_list[0][0][0]
    use_context_cmd = loo.cmd.call_args_list[1][0][0]
    apply_cmd = loo.cmd.call_args_list[2][0][0][0:3]

    assert auth_cmd == [
        'kubectl',
        'auth',
        'can-i',
        'get',
        'deployment'
    ]
    assert use_context_cmd == [
        'kubectl',
        'config',
        'use-context',
        'foo-dev:cluster2',
    ]
    assert apply_cmd == [
        'kubectl',
        'apply',
        '-f',
    ]


def test_deploy_watch(loo):
    # fake arguments
    sys.argv = ['vindaloo', '--noninteractive', 'deploy', '--watch', 'dev', 'cluster1']

    loo.cmd.return_value.stdout.decode.return_value.split.return_value = [
        'foo-registry.com/test/foo:1.0.0',
        'foo-registry.com/test/bar:2.0.0',
    ]

    with chdir('tests/test_roots/simple'):
        loo.main()

    # check arguments docker and kubectl was called with
    assert len(loo.cmd.call_args_list) == 4
    auth_cmd = loo.cmd.call_args_list[0][0][0]
    use_context_cmd = loo.cmd.call_args_list[1][0][0]
    apply_cmd = loo.cmd.call_args_list[2][0][0][0:3]
    rollout_cmd = loo.cmd.call_args_list[3][0][0]

    assert auth_cmd == [
        'kubectl',
        'auth',
        'can-i',
        'get',
        'deployment'
    ]
    assert use_context_cmd == [
        'kubectl',
        'config',
        'use-context',
        'foo-dev:cluster1',
    ]
    assert apply_cmd == [
        'kubectl',
        'apply',
        '-f',
    ]
    assert rollout_cmd == [
        'kubectl',
        'rollout',
        'status',
        'deployment',
        'foobar'
    ]


def test_deploy_configmap(loo):
    # fake arguments
    sys.argv = ['vindaloo', '--noninteractive', 'deploy', 'dev', 'cluster1']

    loo.cmd.return_value.stdout = b'{}'

    with chdir('tests/test_roots/configmaps'):
        loo.main()

    # check arguments docker and kubectl was called with
    assert len(loo.cmd.call_args_list) == 4
    auth_cmd = loo.cmd.call_args_list[0][0][0]
    use_context_cmd = loo.cmd.call_args_list[1][0][0]
    config_map_create_cmd = loo.cmd.call_args_list[2][0][0]
    apply_cmd = loo.cmd.call_args_list[3][0][0][0:3]

    assert auth_cmd == [
        'kubectl',
        'auth',
        'can-i',
        'get',
        'deployment'
    ]
    assert use_context_cmd == [
        'kubectl',
        'config',
        'use-context',
        'foo-dev:cluster1',
    ]
    assert apply_cmd == [
        'kubectl',
        'apply',
        '-f',
    ]

    assert config_map_create_cmd[:4] == [
        'kubectl',
        'create',
        'configmap',
        'test-config-map',
    ]


def test_deploy_to_outdir(loo, test_temp_dir):
    # fake arguments

    sys.argv = ['vindaloo', '--noninteractive', 'deploy-dir', '--apply-output-dir={}'.format(test_temp_dir), 'dev', 'cluster1']

    loo.cmd.return_value.stdout = b'{}'

    with chdir('tests/test_roots/configmaps'):
        loo.main()

    # check arguments docker and kubectl was called with
    assert len(loo.cmd.call_args_list) == 1
    config_map_create_cmd = loo.cmd.call_args_list[0][0][0]

    assert config_map_create_cmd[:4] == [
        'kubectl',
        'create',
        'configmap',
        'test-config-map',
    ]

    assert os.path.isfile(os.path.join(test_temp_dir, "test-config-map_configmap.yaml"))


def test_deploy_config_obj(loo, test_temp_dir):
    # fake arguments
    sys.argv = ['vindaloo', '--noninteractive', 'deploy-dir', '--apply-output-dir={}'.format(test_temp_dir), 'dev', 'cluster1']

    loo.cmd.return_value.stdout.decode.return_value.split.return_value = [
        'foo-registry.com/test/foo:1.0.0',
        'foo-registry.com/test/bar:2.0.0',
    ]

    with chdir('tests/test_roots/obj-config'):
        loo.main()

    assert vindaloo.app.args.cluster == 'cluster1'

    data = json.loads(open(os.path.join(test_temp_dir, 'foo_deployment.yaml'), 'r').read())

    assert data['apiVersion'] == 'extensions/v1beta1'
    assert data['kind'] == 'Deployment'
    assert data['spec']['template']['spec']['volumes'][0]['secret']['secretName'] in ('local-conf', 'cert')
    assert data['spec']['template']['spec']['terminationGracePeriodSeconds'] == 30
    assert data['something'] == {'foo': 'boo'}
    assert data['spec']['template']['spec']['containers'][0]['volumeMounts'][0] == {
        'mountPath': '/cert.pem',
        'name': 'cert',
        'subPath': 'tls.crt'
    }

    data = json.loads(open(os.path.join(test_temp_dir, 'foo_cronjob.yaml'), 'r').read())
    assert data['apiVersion'] == 'batch/v1beta1'
    assert data['kind'] == 'CronJob'
    assert (
        data['spec']['jobTemplate']['spec']['template']['spec']['containers'][0]['image']
        ==
        'registry.hub.docker.com/library/busybox:latest'
    )

    data = json.loads(open(os.path.join(test_temp_dir, 'foo_job.yaml'), 'r').read())
    assert data['apiVersion'] == 'batch/v1'
    assert data['kind'] == 'Job'
    assert data['spec']['template']['metadata']['name'] == 'foo'

    data = json.loads(open(os.path.join(test_temp_dir, 'bar_job.yaml'), 'r').read())
    assert data['apiVersion'] == 'batch/v1'
    assert data['kind'] == 'Job'
    assert data['spec']['template']['metadata']['name'] == 'bar'
    assert data['spec']['template']['spec']['terminationGracePeriodSeconds'] == 30
