import logging
import pytest

from model import *
from model.permissions import *
import test

log = logging.getLogger("dimsum")


@pytest.mark.asyncio
async def test_permissions_basics():
    tw = test.TestWorld()
    await tw.initialize()

    behavior = Acls()
    assert not behavior.has(Permission.READ, "jacob")
    behavior.add(Permission.READ, "jacob")
    assert behavior.has(Permission.READ, "jacob")
    assert not behavior.has(Permission.READ, "carla")
    behavior.add(Permission.READ, "carla")
    assert behavior.has(Permission.READ, "carla")
    assert not behavior.has(Permission.READ, "tomi")
    behavior.add(Permission.READ, "*")
    assert behavior.has(Permission.READ, "tomi")
