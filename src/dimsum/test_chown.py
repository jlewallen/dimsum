import pytest
import freezegun

import handlers
from model import *
import scopes.behavior as behavior
import scopes.carryable as carryable
import scopes
import test


@pytest.mark.asyncio
@freezegun.freeze_time("2019-09-25")
async def test_chown_nothing(snapshot):
    with test.Deterministic():
        tw = test.TestWorld(handlers=[handlers.create(NoopComms())])
        await tw.initialize()
        await tw.failure("chown box")
        await tw.close()


@pytest.mark.asyncio
@freezegun.freeze_time("2019-09-25")
async def test_chown_box_self(snapshot):
    with test.Deterministic():
        tw = test.TestWorld(handlers=[handlers.create(NoopComms())])
        await tw.initialize()
        await tw.success("create thing box")
        await tw.success("chown box")
        await tw.close()


@pytest.mark.asyncio
@freezegun.freeze_time("2019-09-25")
async def test_chown_box_somebody(snapshot):
    with test.Deterministic():
        tw = test.TestWorld(handlers=[handlers.create(NoopComms())])

        await tw.initialize()
        await tw.add_carla()

        await tw.success("create thing box")
        await tw.success("chown box carla")

        await tw.close()