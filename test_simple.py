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
@pytest.mark.skip(reason="todo")
async def test_recipe_simple():
    tw = test.TestWorld()
    await tw.initialize()
    await tw.execute("make IPA")
    await tw.execute("modify alcohol 100")
    assert tw.player.holding[0].details["alcohol"] == 100

    await tw.execute("call this IPA")
    assert len(tw.player.holding) == 1
    await tw.execute("make fancy")
    assert len(tw.player.holding) == 2
    await tw.execute("forget fancy")
    await tw.execute("make fancy")
    assert len(tw.player.holding) == 2
