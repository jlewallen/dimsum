import logging

import model.properties as properties
import pytest

log = logging.getLogger("dimsum")


@pytest.mark.asyncio
async def test_properties():
    map = properties.Common(name="Jacob")
    assert isinstance(map[properties.Name], str)
