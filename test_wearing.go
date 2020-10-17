import pytest

import game
import props
import test


@pytest.mark.asyncio
async def test_simple_wear_and_remove():
    tw = test.TestWorld()
    await tw.initialize()
    await tw.execute("make Shoes")
    await tw.execute("wear shoes")
    assert len(tw.player.holding) == 0
    assert len(tw.player.wearing) == 1

    await tw.execute("remove shoes")
    assert len(tw.player.holding) == 1
    assert len(tw.player.wearing) == 0
