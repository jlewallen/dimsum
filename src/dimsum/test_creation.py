import logging
import freezegun
import pytest

import model.entity as entity
import model.game as game
import model.things as things
import model.world as world
import model.reply as reply
import model.visual as visual

import serializing

import handlers

import test

log = logging.getLogger("dimsum")


@pytest.mark.asyncio
@freezegun.freeze_time("2019-09-25")
async def test_create_thing(snapshot):
    with test.Deterministic():
        tw = test.TestWorld(handlers=[handlers.create(visual.NoopComms())])
        await tw.initialize()
        await tw.success("create thing Box")
        snapshot.assert_match(await tw.to_json(), "world.json")


@pytest.mark.asyncio
@freezegun.freeze_time("2019-09-25")
async def test_create_area(snapshot):
    with test.Deterministic():
        tw = test.TestWorld(handlers=[handlers.create(visual.NoopComms())])
        await tw.initialize()
        await tw.success("create area Treehouse")
        snapshot.assert_match(await tw.to_json(), "world.json")


@pytest.mark.asyncio
@freezegun.freeze_time("2019-09-25")
async def test_create_exit(snapshot):
    with test.Deterministic():
        tw = test.TestWorld(handlers=[handlers.create(visual.NoopComms())])
        await tw.initialize()
        await tw.success("create exit Window")
        snapshot.assert_match(await tw.to_json(), "world.json")
