import logging
import pytest

import game
import reply
import test

log = logging.getLogger("dimsum")


@pytest.mark.asyncio
async def test_quantified_drop_partial_and_hold():
    tw = test.TestWorld()

    await tw.initialize()
    await tw.success("make 20 Coin")
    assert len(tw.player.holding) == 1
    assert len(tw.area.entities()) == 1
    assert len(tw.world.items()) == 1

    await tw.success("drop 5 coin")
    assert len(tw.player.holding) == 1
    assert len(tw.area.entities()) == 2
    assert tw.player.holding[0].quantity == 15
    assert tw.area.entities()[0].quantity == 5
    assert tw.player.holding[0].key in tw.world.entities  # Meh
    assert len(tw.world.items()) == 2

    await tw.success("hold coin")
    assert len(tw.player.holding) == 1
    assert len(tw.area.entities()) == 1
    assert len(tw.world.items()) == 1

    await tw.success("drop 5 coin")
    assert len(tw.player.holding) == 1
    assert len(tw.area.entities()) == 2
    assert len(tw.world.items()) == 2

    await tw.success("drop 5 coin")
    assert len(tw.player.holding) == 1
    assert len(tw.area.entities()) == 2
    assert tw.player.holding[0].quantity == 10
    assert tw.area.entities()[0].quantity == 10
    assert len(tw.world.items()) == 2


@pytest.mark.asyncio
async def test_quantified_hold_number():
    tw = test.TestWorld()

    await tw.initialize()
    await tw.success("make 20 Coin")
    await tw.success("drop 20 coin")
    assert len(tw.player.holding) == 0
    assert len(tw.area.entities()) == 2
    await tw.success("hold 10 coin")
    assert len(tw.player.holding) == 1
    assert len(tw.area.entities()) == 2


@pytest.mark.asyncio
async def test_quantified_drop_all():
    tw = test.TestWorld()

    await tw.initialize()
    await tw.success("make 20 Coin")
    assert len(tw.player.holding) == 1
    assert len(tw.area.entities()) == 1
    assert len(tw.world.items()) == 1

    await tw.success("drop 20 coin")
    assert len(tw.player.holding) == 0
    assert len(tw.area.entities()) == 2
    assert tw.area.holding[0].quantity == 20
    assert len(tw.world.items()) == 1


@pytest.mark.asyncio
async def test_quantified_drop_inflected():
    tw = test.TestWorld()

    await tw.initialize()

    assert len(tw.player.holding) == 0
    await tw.success("make 20 Coin")
    assert len(tw.player.holding) == 1

    assert len(tw.area.entities()) == 1
    await tw.success("drop 10 coins")
    assert len(tw.player.holding) == 1
    assert len(tw.area.entities()) == 2


@pytest.mark.asyncio
async def test_quantified_from_recipe_holding_template(caplog):
    caplog.set_level(logging.INFO)
    tw = test.TestWorld()

    await tw.initialize()
    await tw.success("make Gold Coin")
    await tw.success("call this cash")
    r = await tw.success("make 4 cash")
    assert r.item.quantity == 5
    assert len(tw.player.holding) == 1
    assert len(tw.area.entities()) == 1

    await tw.success("look down")
    assert tw.player.holding[0].quantity == 5


@pytest.mark.asyncio
async def test_quantified_from_recipe(caplog):
    caplog.set_level(logging.INFO)
    tw = test.TestWorld()

    await tw.initialize()
    await tw.success("make Gold Coin")
    await tw.success("call this cash")
    item = tw.player.holding[0]
    assert item

    await tw.success("obliterate")
    assert item.props.destroyed

    await tw.success("make 20 cash")
    assert len(tw.player.holding) == 1
    assert len(tw.area.entities()) == 1

    await tw.success("make 20 cash")
    assert len(tw.player.holding) == 1
    assert len(tw.area.entities()) == 1

    await tw.success("look down")
    assert tw.player.holding[0].quantity == 40
