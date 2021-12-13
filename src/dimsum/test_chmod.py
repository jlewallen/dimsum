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
async def test_chmod_nothing(snapshot):
    with test.Deterministic():
        tw = test.TestWorld(handlers=[handlers.create(NoopComms())])
        await tw.initialize()
        await tw.failure("chmod box")
        await tw.close()


@pytest.mark.asyncio
@freezegun.freeze_time("2019-09-25")
async def test_chmod_ls(snapshot):
    with test.Deterministic():
        tw = test.TestWorld(handlers=[handlers.create(NoopComms())])
        await tw.initialize()
        await tw.success("create thing Box")
        await tw.success("chmod box")
        await tw.close()


@pytest.mark.asyncio
@freezegun.freeze_time("2019-09-25")
async def test_chmod_entity(snapshot):
    with test.Deterministic():
        tw = test.TestWorld(handlers=[handlers.create(NoopComms())])
        await tw.initialize()
        await tw.success("create thing Box")
        await tw.success("chmod box . write owner")
        await tw.close()
