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
    assert len(tw.world.items()) == 1

    await tw.execute("drop 5 coin")
    assert len(tw.player.holding) == 1
    assert len(tw.area.items) == 1
    assert tw.player.holding[0].quantity == 15
    assert tw.area.items[0].quantity == 5
    assert tw.player.holding[0].key in tw.world.entities  # Meh
    assert len(tw.world.items()) == 2

    await tw.execute("hold coin")
    assert len(tw.player.holding) == 1
    assert len(tw.area.items) == 0
    assert len(tw.world.items()) == 1

    await tw.execute("drop 5 coin")
    assert len(tw.player.holding) == 1
    assert len(tw.area.items) == 1
    assert len(tw.world.items()) == 2

    await tw.execute("drop 5 coin")
    assert len(tw.player.holding) == 1
    assert len(tw.area.items) == 1
    assert tw.player.holding[0].quantity == 10
    assert tw.area.items[0].quantity == 10
    assert len(tw.world.items()) == 2


@pytest.mark.asyncio
async def test_quantified_drop_all():
    tw = test.TestWorld()

    await tw.initialize()
    await tw.execute("make 20 Coin")
    assert len(tw.player.holding) == 1
    assert len(tw.area.items) == 0
    assert len(tw.world.items()) == 1

    await tw.execute("drop 20 coin")
    assert len(tw.player.holding) == 0
    assert len(tw.area.items) == 1
    assert tw.area.here[1].quantity == 20
    assert len(tw.world.items()) == 1


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


@pytest.mark.asyncio
async def test_quantified_from_recipe_holding_template(caplog):
    caplog.set_level(logging.INFO)
    tw = test.TestWorld()

    await tw.initialize()
    await tw.execute("make Gold Coin")
    await tw.execute("call this cash")
    r = await tw.execute("make 4 cash")
    assert isinstance(r, game.Success)
    assert r.item.quantity == 5
    assert len(tw.player.holding) == 1
    assert len(tw.area.items) == 0

    await tw.execute("look down")
    assert tw.player.holding[0].quantity == 5


@pytest.mark.asyncio
async def test_quantified_from_recipe(caplog):
    caplog.set_level(logging.INFO)
    tw = test.TestWorld()

    await tw.initialize()
    await tw.execute("make Gold Coin")
    await tw.execute("call this cash")
    await tw.execute("obliterate")

    await tw.execute("make 20 cash")
    assert len(tw.player.holding) == 1
    assert len(tw.area.items) == 0

    await tw.execute("make 20 cash")
    assert len(tw.player.holding) == 1
    assert len(tw.area.items) == 0

    await tw.execute("look down")
    assert tw.player.holding[0].quantity == 40
