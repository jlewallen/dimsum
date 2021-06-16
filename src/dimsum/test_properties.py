import pytest
import logging

import properties
import serializing

log = logging.getLogger("dimsum")


@pytest.mark.asyncio
async def test_properties():
    map = properties.Common(name="Jacob")
    assert isinstance(map[properties.Name], str)