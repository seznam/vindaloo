import json
import os
import sys

import vindaloo
from utils import chdir


def test_deploy(loo):
    # fake arguments
    sys.argv = ['vindaloo', '--noninteractive', 'deploy', 'dev', 'ko']

    loo.cmd.return_value.stdout.decode.return_value.split.return_value = [
        'doc.ker.dev.dszn.cz/test/foo:1.0.0',
        'doc.ker.dev.dszn.cz/test/bar:2.0.0',
    ]

    with chdir('tests/test_roots/simple'):
        loo.main()

    assert vindaloo.app.args.cluster == 'ko'

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
        'foo-dev-ko',
    ]
    assert apply_cmd == [
        'kubectl',
        'apply',
        '-f',
    ]


def test_deploy_one_cluster(loo):
    # fake arguments
    sys.argv = ['vindaloo', '--noninteractive', 'deploy', 'dev', 'ng']

    loo.cmd.return_value.stdout.decode.return_value.split.return_value = [
        'doc.ker.dev.dszn.cz/test/foo:1.0.0',
        'doc.ker.dev.dszn.cz/test/bar:2.0.0',
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
        'foo-dev-ng',
    ]
    assert apply_cmd == [
        'kubectl',
        'apply',
        '-f',
    ]


def test_deploy_watch(loo):
    # fake arguments
    sys.argv = ['vindaloo', '--noninteractive', 'deploy', '--watch', 'dev', 'ko']

    loo.cmd.return_value.stdout.decode.return_value.split.return_value = [
        'doc.ker.dev.dszn.cz/test/foo:1.0.0',
        'doc.ker.dev.dszn.cz/test/bar:2.0.0',
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
        'foo-dev-ko',
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
    sys.argv = ['vindaloo', '--noninteractive', 'deploy', 'dev', 'ko']

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
        'foo-dev-ko',
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

    sys.argv = ['vindaloo', '--noninteractive', 'deploy', '--apply-output-dir={}'.format(test_temp_dir), 'dev', 'ko']

    loo.cmd.return_value.stdout = b'{}'

    with chdir('tests/test_roots/configmaps'):
        loo.main()

    # check arguments docker and kubectl was called with
    assert len(loo.cmd.call_args_list) == 2
    auth_cmd = loo.cmd.call_args_list[0][0][0]
    config_map_create_cmd = loo.cmd.call_args_list[1][0][0]

    assert auth_cmd == [
        'kubectl',
        'auth',
        'can-i',
        'get',
        'deployment'
    ]

    assert config_map_create_cmd[:4] == [
        'kubectl',
        'create',
        'configmap',
        'test-config-map',
    ]

    assert os.path.isfile(os.path.join(test_temp_dir, "test-config-map_configmap.yaml"))


def test_deploy_config_obj(loo, test_temp_dir):
    # fake arguments
    sys.argv = ['vindaloo', '--noninteractive', 'deploy', '--apply-output-dir={}'.format(test_temp_dir), 'dev', 'ko']

    loo.cmd.return_value.stdout.decode.return_value.split.return_value = [
        'doc.ker.dev.dszn.cz/test/foo:1.0.0',
        'doc.ker.dev.dszn.cz/test/bar:2.0.0',
    ]

    with chdir('tests/test_roots/obj-config'):
        loo.main()

    assert vindaloo.app.args.cluster == 'ko'

    # check arguments docker and kubectl was called with
    assert len(loo.cmd.call_args_list) == 1
    auth_cmd = loo.cmd.call_args_list[0][0][0]

    assert auth_cmd == [
        'kubectl',
        'auth',
        'can-i',
        'get',
        'deployment'
    ]

    data = json.loads(open(os.path.join(test_temp_dir, 'foo_deployment.yaml'), 'r').read())

    assert data['apiVersion'] == 'extensions/v1beta1'
    assert data['kind'] == 'Deployment'
    assert data['spec']['template']['spec']['volumes'][0]['secret']['secretName'] == 'local-conf'
    assert data['something'] == {'foo': 'boo'}

    data = json.loads(open(os.path.join(test_temp_dir, 'foo_cronjob.yaml'), 'r').read())
    assert data['apiVersion'] == 'batch/v1beta1'
    assert data['kind'] == 'CronJob'

    data = json.loads(open(os.path.join(test_temp_dir, 'foo_job.yaml'), 'r').read())
    assert data['apiVersion'] == 'batch/v1'
    assert data['kind'] == 'Job'
    assert data['spec']['template']['metadata']['name'] == 'foo'

    data = json.loads(open(os.path.join(test_temp_dir, 'bar_job.yaml'), 'r').read())
    assert data['apiVersion'] == 'batch/v1'
    assert data['kind'] == 'Job'
    assert data['spec']['template']['metadata']['name'] == 'bar'
