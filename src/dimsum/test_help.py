import logging
import pytest
import freezegun

import handlers
from model import *
import scopes.behavior as behavior
import scopes.carryable as carryable
import scopes
import test

log = logging.getLogger("dimsum")


@pytest.mark.asyncio
@freezegun.freeze_time("2019-09-25")
async def test_help(snapshot):
    with test.Deterministic():
        tw = test.TestWorld(handlers=[handlers.create(NoopComms())])
        await tw.initialize()
        await tw.success("help")


@pytest.mark.asyncio
@freezegun.freeze_time("2019-09-25")
async def test_help_create_page(snapshot):
    with test.Deterministic():
        tw = test.TestWorld(handlers=[handlers.create(NoopComms())])
        await tw.initialize()
        await tw.success("help creation")
        await tw.success("help creation create")
        await tw.success("help creation")
