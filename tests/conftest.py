import sys
import os
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
    return loo
