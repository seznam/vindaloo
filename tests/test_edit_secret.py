import json
import sys

import pytest
from utils import chdir

from vindaloo.vindaloo import RefreshException

TEST_JSON = """{
    "apiVersion": "v1",
    "items": [
        {
            "apiVersion": "v1",
            "data": {
                "app.local.conf": "ZmVqaw=="
            },
            "kind": "Secret",
            "metadata": {
                "name": "sos-core-local-conf"
            },
            "type": "Opaque"
        },
        {
            "apiVersion": "v1",
            "data": {
                "password": "ZmVqaw=="
            },
            "kind": "Secret",
            "metadata": {
                "creationTimestamp": "2019-02-06T13:29:55Z",
                "name": "sos-db-master"
            },
            "type": "Opaque"
        }
    ],
    "kind": "List",
    "metadata": {
        "resourceVersion": "",
        "selfLink": ""
    }
}
"""


def test_parse_secrets(loo):
    with chdir('tests/test_roots/simple'):
        res = loo._parse_secrets(json.loads(TEST_JSON))
        assert len(res) == 2


def test_commit_secret_values(loo):

    with chdir('tests/test_roots/simple'):
        loo.changed_secrets = {"a": b"b"}
        with pytest.raises(RefreshException):
            loo._commit_secret_values({"name": "XXX"})
        assert loo.cmd.call_args[0][0] == ['kubectl', 'patch', 'secret', 'XXX',  '-p', '{"data":{"a":"Yg=="}}']