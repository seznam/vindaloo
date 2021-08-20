import json
import sys
from unittest import mock

import yaml

from utils import chdir
from vindaloo.vindaloo import Vindaloo
from vindaloo.convert import get_obj_repr_from_dict

EXPECTED = """
import vindaloo
from vindaloo.objects import Deployment

versions = vindaloo.app.versions

DEPLOYMENT = Deployment(
    name="nginx",
    replicas=3,
    containers={
        'nginx': {
            'image': "docker.repo/bar/foo-web:" + versions['docker.repo/bar/foo-web'],
            'ports': [{'containerPort': 80}, {'containerPort': 8080}],
            'env': {'APP_ENV': 'production'},
        },
    },
    volumes=None,
    annotations=None, 
    metadata={'labels': {}}, 
    labels=None,
    spec_annotations={'please-redeploy-dis': '14'},
    termination_grace_period=30,
)

K8S_OBJECTS = {
    "deployment": [DEPLOYMENT],
}
"""


def test_convert_deployment():
    with chdir(f'tests/test_roots/convert'):
        with open('deployment.yaml', 'r') as fp:
            manifest_data = yaml.load(fp, Loader=yaml.Loader)
        res = get_obj_repr_from_dict(manifest_data)

    assert res == EXPECTED


def test_convert_deployment2(capsys):
    loo = Vindaloo()
    loo.args = mock.Mock()
    loo.args.quiet = False
    loo.args.manifest = 'deployment.yaml'

    with chdir(f'tests/test_roots/convert'):
        loo.convert_manifest()

    output = capsys.readouterr().out.strip()
    assert output == EXPECTED.strip()
