import logging
import pytest

import test


@pytest.fixture(scope="function")
def silence_dynamic_errors(caplog):
    caplog.set_level(logging.CRITICAL, "dimsum.dynamic.errors")
    yield


@pytest.fixture(scope="function")
def deterministic():
    with test.Deterministic():
        yield
