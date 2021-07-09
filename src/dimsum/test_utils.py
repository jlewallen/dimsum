import logging
import pytest


@pytest.fixture(scope="function")
def silence_dynamic_errors(caplog):
    caplog.set_level(logging.CRITICAL, "dimsum.dynamic.errors")
    yield
