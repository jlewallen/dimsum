import logging

from model import *
import pytest

log = logging.getLogger("dimsum")


@pytest.mark.asyncio
async def test_properties():
    map = Common(name="Jacob")
    assert isinstance(map["name"], str)
