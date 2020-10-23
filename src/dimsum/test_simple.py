import pytest
import logging

import props
import entity
import game
import things
import world
import reply
import serializing
import persistence
import test

log = logging.getLogger("dimsum")


@pytest.mark.asyncio
async def test_simple_action_verbs():
    tw = test.TestWorld()
    await tw.initialize()
    await tw.add_carla()
    for verb in ["kiss", "heal", "hug", "tickle", "poke"]:
        await tw.success(verb + " carla")
    assert len(tw.player.holding) == 0


@pytest.mark.asyncio
async def test_obliterate():
    tw = test.TestWorld()
    await tw.initialize()
    await tw.success("make Hammer")
    assert len(tw.player.holding) == 1
    await tw.success("obliterate")
    assert len(tw.player.holding) == 0


@pytest.mark.asyncio
async def test_recipe_simple():
    tw = test.TestWorld()
    await tw.initialize()
    await tw.success("make IPA")
    await tw.success("modify alcohol 100")
    assert tw.player.holding[0].nutrition.properties["alcohol"] == 100

    assert len(tw.player.memory.keys()) == 0
    await tw.success("call this Fancy IPA")
    assert len(tw.player.memory.keys()) == 1

    await tw.success("make fancy")
    assert len(tw.player.holding) == 1
