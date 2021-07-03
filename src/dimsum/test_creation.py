import pytest
import logging
import lark

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
async def test_create_thing():
    tw = test.TestWorld(handlers=[handlers.create(visual.NoopComms())])
    await tw.initialize()
    await tw.success("create thing Box")
    # ASSERT match of entities
