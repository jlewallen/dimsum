import pytest
import logging

import entity
import game
import things
import world
import reply
import serializing
import persistence
import carryable
import test

log = logging.getLogger("dimsum")


@pytest.mark.asyncio
async def test_hold_missing_item():
    tw = test.TestWorld()
    await tw.initialize()
    await tw.failure("hold hammer")
    assert len(tw.player.make(carryable.ContainingMixin).holding) == 0


@pytest.mark.asyncio
async def test_make_hold_drop():
    tw = test.TestWorld()
    await tw.initialize()
    await tw.success("make Hammer")
    assert len(tw.player.make(carryable.ContainingMixin).holding) == 1
    await tw.success("drop")
    assert len(tw.player.make(carryable.ContainingMixin).holding) == 0
    await tw.success("hold hammer")
    assert len(tw.player.make(carryable.ContainingMixin).holding) == 1


@pytest.mark.asyncio
async def test_make_hold_drop_specific():
    tw = test.TestWorld()
    await tw.initialize()
    await tw.success("make Hammer")
    await tw.success("make Ball")
    assert len(tw.player.make(carryable.ContainingMixin).holding) == 2
    await tw.success("drop ball")
    assert len(tw.player.make(carryable.ContainingMixin).holding) == 1
    await tw.success("hold ball")
    assert len(tw.player.make(carryable.ContainingMixin).holding) == 2


@pytest.mark.asyncio
async def test_put_coin_inside_box_and_then_take_out(caplog):
    caplog.set_level(logging.INFO)
    tw = test.TestWorld()
    await tw.initialize()
    await tw.success("make Coin")
    await tw.success("make Box")
    assert len(tw.player.make(carryable.ContainingMixin).holding) == 2
    await tw.failure("put coin in box")
    await tw.failure("open box")
    await tw.success("drop coin")
    await tw.success("modify capacity 1")
    await tw.success("hold coin")
    # await tw.success("open box")
    await tw.success("put coin in box")
    assert len(tw.player.make(carryable.ContainingMixin).holding) == 1
    await tw.success("look down")
    assert (
        len(tw.world.find_entity_by_name("Box").make(carryable.ContainingMixin).holding)
        == 1
    )
    await tw.success("close box")
    await tw.failure("take coin out of box")
    await tw.success("open box")
    await tw.success("take coin out of box")
    assert (
        len(tw.world.find_entity_by_name("Box").make(carryable.ContainingMixin).holding)
        == 0
    )
    assert len(tw.player.make(carryable.ContainingMixin).holding) == 2


@pytest.mark.asyncio
async def test_put_coin_inside_box_and_then_look_inside(caplog):
    caplog.set_level(logging.INFO)
    tw = test.TestWorld()
    await tw.initialize()
    await tw.success("make Box")
    await tw.success("modify capacity 1")
    await tw.success("close box")
    await tw.success("make Coin")
    assert len(tw.player.make(carryable.ContainingMixin).holding) == 2
    coin = tw.player.make(carryable.ContainingMixin).holding[1]
    assert "Coin" in coin.props.name
    await tw.failure("put coin in box")
    await tw.success("open box")
    await tw.success("put coin in box")
    assert len(tw.player.make(carryable.ContainingMixin).holding) == 1
    r = await tw.execute("look in box")
    assert isinstance(r, reply.EntitiesObservation)
    assert coin in r.entities


@pytest.mark.asyncio
async def test_lock_with_new_key(caplog):
    caplog.set_level(logging.INFO)
    tw = test.TestWorld()
    await tw.initialize()
    await tw.success("make Box")
    await tw.success("modify capacity 1")
    await tw.success("lock box")
    assert len(tw.player.make(carryable.ContainingMixin).holding) == 2
    await tw.failure("open box")
    await tw.success("unlock box")
    # await tw.success("open box")
    assert len(tw.player.make(carryable.ContainingMixin).holding) == 2
    await tw.success("lock box with key")
    assert len(tw.player.make(carryable.ContainingMixin).holding) == 2
    await tw.success("unlock box")
    assert len(tw.player.make(carryable.ContainingMixin).holding) == 2


@pytest.mark.asyncio
async def test_try_unlock_wrong_key(caplog):
    tw = test.TestWorld()
    await tw.initialize()
    await tw.success("make Box")
    await tw.success("lock box")
    assert len(tw.player.make(carryable.ContainingMixin).holding) == 2
    await tw.success("drop key")
    assert len(tw.player.make(carryable.ContainingMixin).holding) == 1

    await tw.success("make Chest")
    await tw.success("lock chest")
    await tw.success("drop chest")
    await tw.failure("unlock box with key")


@pytest.mark.asyncio
async def test_make_and_open_container(caplog):
    tw = test.TestWorld()
    await tw.initialize()
    await tw.success("make Box")
    await tw.success("modify capacity 1")
    await tw.failure("open box")
    await tw.success("close box")
    await tw.success("open box")
    await tw.success("close box")


@pytest.mark.asyncio
async def test_loose_item_factory_pour_ipa_from_keg(caplog):
    caplog.set_level(logging.INFO)
    tw = test.TestWorld()
    await tw.initialize()
    await tw.success("make Beer Keg")
    await tw.success("modify capacity 100")
    await tw.failure("pour from Keg")
    await tw.success("modify pours Jai Alai IPA")
    await tw.failure("pour from Keg")
    await tw.success("drop keg")  # TODO modify <noun>
    # This could eventually pour on the floor.
    await tw.success("make Mug")
    await tw.success("modify capacity 10")
    await tw.success("hold keg")
    await tw.success("pour from Keg")
    r = await tw.success("look in mug")
    assert len(r.entities) == 1
    assert "Alai" in r.entities[0].props.name
    assert r.entities[0].make(carryable.CarryableMixin).loose
    assert tw.world.find_by_key(r.entities[0].key)


@pytest.mark.asyncio
async def test_unable_to_hold_loose_item(caplog):
    caplog.set_level(logging.INFO)
    tw = test.TestWorld()
    await tw.initialize()
    await tw.success("make Beer Keg")
    await tw.success("modify capacity 100")
    await tw.success("modify pours Jai Alai IPA")
    await tw.success("drop keg")  # TODO modify <noun>
    # This could eventually pour on the floor.
    await tw.success("make Mug")
    await tw.success("modify capacity 10")
    await tw.success("hold keg")
    await tw.success("pour from Keg")
    await tw.failure("take Alai out of keg")
    await tw.success("drink Alai")
