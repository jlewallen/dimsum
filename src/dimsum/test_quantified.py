import logging
import pytest

import game
import reply
import carryable
import test

log = logging.getLogger("dimsum")


@pytest.mark.asyncio
async def test_quantified_drop_partial_and_hold():
    tw = test.TestWorld()

    await tw.initialize()
    await tw.success("make 20 Coin")
    assert len(tw.player.make(carryable.Containing).holding) == 1
    assert len(tw.area.make(carryable.Containing).holding) == 0
    assert len(tw.world.entities) == 4

    await tw.success("drop 5 coin")
    assert len(tw.player.make(carryable.Containing).holding) == 1
    assert len(tw.area.make(carryable.Containing).holding) == 1
    assert (
        tw.player.make(carryable.Containing)
        .holding[0]
        .make(carryable.Carryable)
        .quantity
        == 15
    )
    assert (
        tw.area.make(carryable.Containing)
        .entities()[0]
        .make(carryable.Carryable)
        .quantity
        == 5
    )
    assert (
        tw.player.make(carryable.Containing).holding[0].key in tw.world.entities
    )  # Meh
    assert len(tw.world.entities) == 5

    await tw.success("hold coin")
    assert len(tw.player.make(carryable.Containing).holding) == 1
    assert len(tw.area.make(carryable.Containing).holding) == 0
    assert len(tw.world.entities) == 4

    await tw.success("drop 5 coin")
    assert len(tw.player.make(carryable.Containing).holding) == 1
    assert len(tw.area.make(carryable.Containing).holding) == 1
    assert len(tw.world.entities) == 5

    await tw.success("drop 5 coin")
    assert len(tw.player.make(carryable.Containing).holding) == 1
    assert len(tw.area.make(carryable.Containing).holding) == 1
    assert (
        tw.player.make(carryable.Containing)
        .holding[0]
        .make(carryable.Carryable)
        .quantity
        == 10
    )
    assert (
        tw.area.make(carryable.Containing)
        .entities()[0]
        .make(carryable.Carryable)
        .quantity
        == 10
    )
    assert len(tw.world.entities) == 5


@pytest.mark.asyncio
async def test_quantified_hold_number():
    tw = test.TestWorld()

    await tw.initialize()
    await tw.success("make 20 Coin")
    await tw.success("drop 20 coin")
    assert len(tw.player.make(carryable.Containing).holding) == 0
    assert len(tw.area.make(carryable.Containing).holding) == 1
    await tw.success("hold 10 coin")
    assert len(tw.player.make(carryable.Containing).holding) == 1
    assert len(tw.area.make(carryable.Containing).holding) == 1


@pytest.mark.asyncio
async def test_quantified_drop_all():
    tw = test.TestWorld()

    await tw.initialize()
    assert len(tw.world.entities) == 3
    await tw.success("make 20 Coin")
    assert len(tw.player.make(carryable.Containing).holding) == 1
    assert len(tw.area.make(carryable.Containing).holding) == 0
    assert len(tw.world.entities) == 4

    await tw.success("drop 20 coin")
    assert len(tw.player.make(carryable.Containing).holding) == 0
    assert len(tw.area.make(carryable.Containing).holding) == 1
    assert (
        tw.area.make(carryable.Containing).holding[0].make(carryable.Carryable).quantity
        == 20
    )
    assert len(tw.world.entities) == 4


@pytest.mark.asyncio
async def test_quantified_drop_inflected():
    tw = test.TestWorld()

    await tw.initialize()

    assert len(tw.player.make(carryable.Containing).holding) == 0
    await tw.success("make 20 Coin")
    assert len(tw.player.make(carryable.Containing).holding) == 1

    assert len(tw.area.make(carryable.Containing).holding) == 0
    await tw.success("drop 10 coin")
    assert len(tw.player.make(carryable.Containing).holding) == 1
    assert len(tw.area.make(carryable.Containing).holding) == 1


@pytest.mark.asyncio
async def test_quantified_from_recipe_holding_template(caplog):
    tw = test.TestWorld()

    await tw.initialize()
    await tw.success("make Gold Coin")
    await tw.success("call this cash")
    r = await tw.success("make 4 cash")
    assert r.item.make(carryable.Carryable).quantity == 5
    assert len(tw.player.make(carryable.Containing).holding) == 1
    assert len(tw.area.make(carryable.Containing).holding) == 0

    await tw.success("look down")
    assert (
        tw.player.make(carryable.Containing)
        .holding[0]
        .make(carryable.Carryable)
        .quantity
        == 5
    )


@pytest.mark.asyncio
async def test_quantified_from_recipe(caplog):
    tw = test.TestWorld()

    await tw.initialize()
    await tw.success("make Gold Coin")
    await tw.success("call this cash")
    item = tw.player.make(carryable.Containing).holding[0]
    assert item

    await tw.success("obliterate")
    assert item.props.destroyed

    await tw.success("make 20 cash")
    assert len(tw.player.make(carryable.Containing).holding) == 1
    assert len(tw.area.make(carryable.Containing).holding) == 0

    await tw.success("make 20 cash")
    assert len(tw.player.make(carryable.Containing).holding) == 1
    assert len(tw.area.make(carryable.Containing).holding) == 0

    await tw.success("look down")
    assert (
        tw.player.make(carryable.Containing)
        .holding[0]
        .make(carryable.Carryable)
        .quantity
        == 40
    )
