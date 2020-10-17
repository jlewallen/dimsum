import logging
import pytest

import game
import props
import test


@pytest.mark.asyncio
async def test_quantified_drop_partial_and_hold():
    tw = test.TestWorld()

    await tw.initialize()
    await tw.execute("make 20 Coin")
    assert len(tw.player.holding) == 1
    assert len(tw.area.items) == 0

    await tw.execute("drop 5 coin")
    assert len(tw.player.holding) == 1
    assert len(tw.area.items) == 1
    assert tw.player.holding[0].quantity == 15
    assert tw.area.items[0].quantity == 5

    await tw.execute("hold coin")
    assert len(tw.player.holding) == 1
    assert len(tw.area.items) == 0

    await tw.execute("drop 5 coin")
    assert len(tw.player.holding) == 1
    assert len(tw.area.items) == 1

    await tw.execute("drop 5 coin")
    assert len(tw.player.holding) == 1
    assert len(tw.area.items) == 1
    assert tw.player.holding[0].quantity == 10
    assert tw.area.items[0].quantity == 10


@pytest.mark.asyncio
async def test_quantified_drop_all():
    tw = test.TestWorld()

    await tw.initialize()
    await tw.execute("make 20 Coin")
    assert len(tw.player.holding) == 1
    assert len(tw.area.items) == 0

    await tw.execute("drop 20 coin")
    assert len(tw.player.holding) == 0
    assert len(tw.area.items) == 1
    assert tw.area.here[1].quantity == 20


@pytest.mark.asyncio
async def test_quantified_drop_inflected():
    tw = test.TestWorld()

    await tw.initialize()

    assert len(tw.player.holding) == 0
    await tw.execute("make 20 Coin")
    assert len(tw.player.holding) == 1

    assert len(tw.area.items) == 0
    await tw.execute("drop 10 coins")
    assert len(tw.player.holding) == 1
    assert len(tw.area.items) == 1
