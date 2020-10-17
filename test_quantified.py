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

    assert len(tw.player.holding) == 1
    assert len(tw.area.here) == 1

    await tw.execute("drop 5 coin")

    assert len(tw.player.holding) == 1
    assert len(tw.area.here) == 2

    assert tw.player.holding[0].quantity == 15
    assert tw.area.here[1].quantity == 5


@pytest.mark.asyncio
async def test_quantified_drop_all():
    tw = test.TestWorld()

    await tw.initialize()
    await tw.execute("make 20 Coin")

    assert len(tw.player.holding) == 1
    assert len(tw.area.here) == 1

    await tw.execute("drop 20 coin")

    assert len(tw.player.holding) == 0
    assert len(tw.area.here) == 2

    assert tw.area.here[1].quantity == 20


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
