import pytest

import game
import props
import test


@pytest.mark.asyncio
async def test_simple_wear_and_remove():
    tw = test.TestWorld()
    await tw.initialize()
    await tw.execute("hold hammer")
    assert len(tw.player.holding) == 0
