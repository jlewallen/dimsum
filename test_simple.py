import pytest

import game
import props
import test


@pytest.mark.asyncio
async def test_hold_missing_item():
    tw = test.TestWorld()
    await tw.initialize()
    await tw.execute("hold hammer")
    assert len(tw.player.holding) == 0


@pytest.mark.asyncio
async def test_make_hold_drop():
    tw = test.TestWorld()
    await tw.initialize()
    await tw.execute("make Hammer")
    assert len(tw.player.holding) == 1
    await tw.execute("drop")
    assert len(tw.player.holding) == 0
    await tw.execute("hold hammer")
    assert len(tw.player.holding) == 1


@pytest.mark.asyncio
async def test_make_hold_drop_specific():
    tw = test.TestWorld()
    await tw.initialize()
    await tw.execute("make Hammer")
    await tw.execute("make Ball")
    assert len(tw.player.holding) == 2
    await tw.execute("drop ball")
    assert len(tw.player.holding) == 1
    await tw.execute("hold ball")
    assert len(tw.player.holding) == 2


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
    assert tw.player.holding[0].details["alcohol"] == 100

    assert len(tw.player.memory.keys()) == 0
    await tw.execute("call this Fancy IPA")
    assert len(tw.player.memory.keys()) == 1

    await tw.execute("make fancy")
    assert len(tw.player.holding) == 1


@pytest.mark.asyncio
async def test_look_for():
    tw = test.TestWorld()
    await tw.initialize()
    await tw.execute("look for keys")
