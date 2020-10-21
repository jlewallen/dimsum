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
    for verb in ["kiss", "kick", "heal", "hug", "tickle", "poke"]:
        await tw.execute(verb + " carla")
    assert len(tw.player.holding) == 0


@pytest.mark.asyncio
async def test_obliterate():
    tw = test.TestWorld()
    await tw.initialize()
    await tw.execute("make Hammer")
    assert len(tw.player.holding) == 1
    await tw.execute("obliterate")
    assert len(tw.player.holding) == 0


@pytest.mark.asyncio
async def test_recipe_simple():
    tw = test.TestWorld()
    await tw.initialize()
    await tw.execute("make IPA")
    await tw.execute("modify alcohol 100")
    assert tw.player.holding[0].nutrition.properties["alcohol"] == 100

    assert len(tw.player.memory.keys()) == 0
    await tw.execute("call this Fancy IPA")
    assert len(tw.player.memory.keys()) == 1

    await tw.execute("make fancy")
    assert len(tw.player.holding) == 1
