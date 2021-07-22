from model import *
import pytest


@pytest.mark.asyncio
async def test_properties():
    map = Common(name="Jacob")
    assert isinstance(map["name"], str)
