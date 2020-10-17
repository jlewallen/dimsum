import logging
import pytest

import game
import props
import test


@pytest.mark.asyncio
async def test_quantified():
    tw = test.TestWorld()

    await tw.initialize()
    await tw.execute("make 20 Coin")
    assert len((await tw.execute("look down")).entities) > 0

    await tw.execute("drop 10 coin")
    assert len(tw.player.holding) == 1
    assert tw.player.holding[0].quantity == 10


@pytest.mark.asyncio
@pytest.mark.skip(reason="todo")
async def test_quantified_drop_inflected():
    tw = test.TestWorld()

    r = await tw.initialize()
    r = await tw.execute("make 20 Coin")
    r = await tw.execute("look down")
    assert len(r.entities) > 0

    r = await tw.execute("drop 10 coins")
    logging.warning(r)
