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

import cli.handlers as handlers

import test

log = logging.getLogger("dimsum")


@pytest.mark.asyncio
async def test_say_nothing():
    tw = test.TestWorld(handlers=[handlers.create(visual.NoopComms())])
    await tw.initialize()
    with pytest.raises(lark.exceptions.UnexpectedEOF):
        await tw.failure("say")


@pytest.mark.asyncio
async def test_say_basic():
    tw = test.TestWorld(handlers=[handlers.create(visual.NoopComms())])
    await tw.initialize()
    await tw.success("say hello, world!")


@pytest.mark.asyncio
async def test_say_with_initial_quote():
    tw = test.TestWorld(handlers=[handlers.create(visual.NoopComms())])
    await tw.initialize()
    await tw.success('" hello, world!')
