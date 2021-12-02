import base64
import json
import os
import sys

import pytest
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
    assert len(loo.cmd.call_args_list) == 4
    rev_parse_cmd = loo.cmd.call_args_list[0][0][0]
    auth_cmd = loo.cmd.call_args_list[1][0][0]
    use_context_cmd = loo.cmd.call_args_list[2][0][0]
    apply_cmd = loo.cmd.call_args_list[3][0][0][0:3]

    assert rev_parse_cmd == [
        'git',
        'rev-parse',
        '--short=8',
        'HEAD'
    ]
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
    assert len(loo.cmd.call_args_list) == 4
    rev_parse_cmd = loo.cmd.call_args_list[0][0][0]
    auth_cmd = loo.cmd.call_args_list[1][0][0]
    use_context_cmd = loo.cmd.call_args_list[2][0][0]
    apply_cmd = loo.cmd.call_args_list[3][0][0][0:3]

    assert rev_parse_cmd == [
        'git',
        'rev-parse',
        '--short=8',
        'HEAD'
    ]
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
    assert len(loo.cmd.call_args_list) == 5
    rev_parse_cmd = loo.cmd.call_args_list[0][0][0]
    auth_cmd = loo.cmd.call_args_list[1][0][0]
    use_context_cmd = loo.cmd.call_args_list[2][0][0]
    apply_cmd = loo.cmd.call_args_list[3][0][0][0:3]
    rollout_cmd = loo.cmd.call_args_list[4][0][0]

    assert rev_parse_cmd == [
        'git',
        'rev-parse',
        '--short=8',
        'HEAD'
    ]
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


def test_configmap(loo):
    # fake arguments
    sys.argv = ['vindaloo', '--noninteractive', 'deploy', 'dev', 'cluster1']

    loo.cmd.return_value.stdout = b'{}'

    with chdir('tests/test_roots/configmap'):
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
        'foo-dev:cluster1',
    ]
    assert apply_cmd == [
        'kubectl',
        'apply',
        '-f',
    ]


def test_deploy_to_outdir(loo, test_temp_dir):
    # fake arguments

    sys.argv = ['vindaloo', '--noninteractive', 'deploy-dir', '--apply-output-dir={}'.format(test_temp_dir), 'dev', 'cluster1']

    loo.cmd.return_value.stdout = b'{}'

    with chdir('tests/test_roots/configmap'):
        loo.main()

    assert os.path.isfile(os.path.join(test_temp_dir, "test-config-map_configmap.json"))
    with open(os.path.join(test_temp_dir, "test-config-map_configmap.json"), 'r') as file:
        configmap = json.loads(file.read())
        assert configmap['metadata']['name'] == 'test-config-map'
        assert configmap['data']['file_config_key'] == (
            'some_config_value=123\n'
            'another_config=one,two,three\n'
            'template_config=This value depends on the selected environment.\n'
        )
        assert base64.decodebytes(configmap['binaryData']['simple_binary_key'].encode()) == b'\x76\x69\x6b\x79'
        with open('tests/test_roots/configmap/k8s/templates/binary_config.conf', 'br') as binary_file:
            base64_content = configmap['binaryData']['binary_file_config_key']
            assert base64.decodebytes(base64_content.encode()) == binary_file.read()


@pytest.mark.parametrize('test_root_dir', ['obj-config', 'obj-config-wo-init'])
def test_deploy_config_obj(loo, test_temp_dir, test_root_dir):
    # fake arguments
    sys.argv = ['vindaloo', '--noninteractive', 'deploy-dir', '--apply-output-dir={}'.format(test_temp_dir), 'dev', 'cluster1']

    loo.cmd.return_value.stdout.decode.return_value.split.return_value = [
        'foo-registry.com/test/foo:1.0.0',
        'foo-registry.com/test/bar:2.0.0',
    ]

    with chdir(f'tests/test_roots/{test_root_dir}'):
        loo.main()

    assert vindaloo.app.args.cluster == 'cluster1'

    data = json.loads(open(os.path.join(test_temp_dir, 'foo_deployment.json'), 'r').read())

    assert data['apiVersion'] == 'apps/v1'
    assert data['kind'] == 'Deployment'
    assert data['spec']['selector']['matchLabels']['app'] == 'foo'
    assert data['spec']['template']['spec']['volumes'][0]['secret']['secretName'] == 'local-conf'
    assert data['spec']['template']['spec']['terminationGracePeriodSeconds'] == 30
    assert data['spec']['something'] == {'foo': 'boo'}
    assert data['spec']['template']['spec']['containers'][0]['image'] == 'foo-registry.com/test/foo:1.0.0'
    assert data['spec']['template']['spec']['containers'][0]['volumeMounts'][0] == {
        'mountPath': '/cert.pem',
        'name': 'cert',
        'subPath': 'tls.crt'
    }
    assert data['spec']['template']['spec']['containers'][0]['env'][0] == {
        'name': 'ENV',
        'value': 'dev'
    }
    assert data['spec']['template']['spec']['containers'][0]['ports'][0] == {
        'name': 'proxy',
        'containerPort': 5001,
    }
    assert data['spec']['template']['spec']['containers'][0]['ports'][1] == {
        'name': 'server',
        'containerPort': 5000,
        'protocol': 'UDP',
    }
    assert data['metadata']['annotations']['deploy-cluster'] == 'cluster2'
    assert data['spec']['template']['metadata']['annotations']['log-retention'] == '3w'

    data = json.loads(open(os.path.join(test_temp_dir, 'foo_cronjob.json'), 'r').read())
    assert data['apiVersion'] == 'batch/v1beta1'
    assert data['kind'] == 'CronJob'
    assert (
        data['spec']['jobTemplate']['spec']['template']['spec']['containers'][0]['image']
        ==
        'registry.hub.docker.com/library/busybox:latest'
    )
    assert data['spec']['schedule'] == "0 0 * * *"
    assert data['spec']['jobTemplate']['spec']['template']['spec']['containers'][0]['volumeMounts'][0] == {
        'name': 'localconfig',
        'mountPath': "/app.local.conf",
        'subPath': "app.local.conf",
    }
    assert data['spec']['jobTemplate']['spec']['template']['spec']['containers'][0]['command'] == ['echo', 'z']

    data = json.loads(open(os.path.join(test_temp_dir, 'foo_job.json'), 'r').read())
    assert data['apiVersion'] == 'batch/v1'
    assert data['kind'] == 'Job'
    assert data['spec']['template']['metadata']['name'] == 'foo'

    data = json.loads(open(os.path.join(test_temp_dir, 'bar_job.json'), 'r').read())
    assert data['apiVersion'] == 'batch/v1'
    assert data['kind'] == 'Job'
    assert data['spec']['template']['metadata']['name'] == 'bar'
    assert data['spec']['template']['spec']['terminationGracePeriodSeconds'] == 30

    data = json.loads(open(os.path.join(test_temp_dir, 'foo_service.json'), 'r').read())
    assert data['spec']['type'] == 'NodePort'
    assert data['spec']['ports'][0]['nodePort'] == 30666
    assert data['spec']['ports'][0]['targetPort'] == 5001
    assert data['spec']['loadBalancerIP'] == '10.1.1.1'
    assert data['metadata']['name'] == "foo"
    assert data['metadata']['annotations']['loadbalancer'] == "enabled"
