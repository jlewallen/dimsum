import pytest

import props
import game
import reply
import test


@pytest.mark.asyncio
async def test_wearing_when_unwearable():
    tw = test.TestWorld()
    await tw.initialize()
    await tw.success("make Shoes")
    await tw.failure("wear shoes")
    print(tw.player.holding)
    print(tw.player.wearing)
    assert len(tw.player.holding) == 1
    assert len(tw.player.wearing) == 0


@pytest.mark.asyncio
async def test_simple_wear_and_remove():
    tw = test.TestWorld()
    await tw.initialize()
    await tw.success("make Shoes")
    await tw.success("modify when worn")
    await tw.success("wear shoes")
    assert len(tw.player.holding) == 0
    assert len(tw.player.wearing) == 1

    await tw.success("remove shoes")
    assert len(tw.player.holding) == 1
    assert len(tw.player.wearing) == 0
