import shutil
import sys
import os
import uuid
from unittest import mock

import pytest


sys.path.insert(
    0,
    os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            '..'
        )
    )
)

from vindaloo.vindaloo import Vindaloo


@pytest.fixture
def loo():
    loo = Vindaloo()
    loo.cmd = mock.Mock()
    loo.cmd.return_value.returncode = 0
    loo._check_version = mock.Mock()
    return loo


@pytest.yield_fixture(scope='function')
def test_temp_dir():
    tmpdir_name = "/tmp/{}_test_output".format(uuid.uuid4().hex)
    os.makedirs(tmpdir_name)
    yield tmpdir_name
    shutil.rmtree(tmpdir_name)
