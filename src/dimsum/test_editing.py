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
async def test_edit_thing_missing():
    tw = test.TestWorld(handlers=[handlers.create(visual.NoopComms())])
    await tw.initialize()
    await tw.failure("edit box")


@pytest.mark.asyncio
async def test_edit_here():
    tw = test.TestWorld(handlers=[handlers.create(visual.NoopComms())])
    await tw.initialize()
    await tw.success("edit here")


@pytest.mark.asyncio
async def test_edit_item():
    tw = test.TestWorld(handlers=[handlers.create(visual.NoopComms())])
    await tw.initialize()
    await tw.success("create thing Box")
    await tw.success("edit box")
