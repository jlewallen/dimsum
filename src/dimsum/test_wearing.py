import pytest

import props
import game
import reply
import test


@pytest.mark.asyncio
async def test_wearing_when_unwearable():
    tw = test.TestWorld()
    await tw.initialize()
    await tw.execute("make Shoes")
    r = await tw.execute("wear shoes")
    assert isinstance(r, reply.Failure)
    print(tw.player.holding)
    print(tw.player.wearing)
    assert len(tw.player.holding) == 1
    assert len(tw.player.wearing) == 0


@pytest.mark.asyncio
async def test_simple_wear_and_remove():
    tw = test.TestWorld()
    await tw.initialize()
    await tw.execute("make Shoes")
    await tw.execute("modify when worn")
    await tw.execute("wear shoes")
    assert len(tw.player.holding) == 0
    assert len(tw.player.wearing) == 1

    await tw.execute("remove shoes")
    assert len(tw.player.holding) == 1
    assert len(tw.player.wearing) == 0