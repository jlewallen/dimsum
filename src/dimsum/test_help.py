import json
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
async def test_help(snapshot):
    with test.Deterministic():
        tw = test.TestWorld(handlers=[handlers.create(NoopComms())])
        await tw.initialize()
        await tw.success("help")
        await tw.close()


@pytest.mark.asyncio
@freezegun.freeze_time("2019-09-25")
async def test_help_create_page(snapshot):
    with test.Deterministic():
        tw = test.TestWorld(handlers=[handlers.create(NoopComms())])
        await tw.initialize()
        await tw.failure("help creating")
        await tw.failure("help Creating")
        await tw.success("help CreatingThings")
        await tw.success("help CreatingThings create")
        await tw.success("help CreatingThings")
        await tw.close()


@pytest.mark.asyncio
@freezegun.freeze_time("2019-09-25")
async def test_help_edit_help_root(snapshot):
    with test.Deterministic():
        tw = test.TestWorld(handlers=[handlers.create(NoopComms())])
        await tw.initialize()
        r = await tw.success("edit help")
        assert r.source.version.i == 1
        await tw.close()


@pytest.mark.asyncio
@freezegun.freeze_time("2019-09-25")
async def test_help_edit_help_page(snapshot):
    with test.Deterministic():
        tw = test.TestWorld(handlers=[handlers.create(NoopComms())])
        await tw.initialize()
        await tw.success("edit help CreatingThings")
        await tw.success("help CreatingThings")
        await tw.close()
