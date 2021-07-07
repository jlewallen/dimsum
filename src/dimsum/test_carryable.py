import logging
import test

import model.reply as reply
import model.scopes.carryable as carryable
import pytest

log = logging.getLogger("dimsum")


@pytest.mark.asyncio
async def test_hold_missing_item():
    tw = test.TestWorld()
    await tw.initialize()
    await tw.failure("hold hammer")

    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        assert len(jacob.make(carryable.Containing).holding) == 0


@pytest.mark.asyncio
async def test_make_hold_drop():
    tw = test.TestWorld()
    await tw.initialize()
    await tw.success("make Hammer")

    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        assert len(jacob.make(carryable.Containing).holding) == 1

    await tw.success("drop")

    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        assert len(jacob.make(carryable.Containing).holding) == 0

    await tw.success("hold hammer")

    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        assert len(jacob.make(carryable.Containing).holding) == 1


@pytest.mark.asyncio
async def test_make_hold_drop_specific():
    tw = test.TestWorld()
    await tw.initialize()
    await tw.success("make Hammer")
    await tw.success("make Ball")

    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        assert len(jacob.make(carryable.Containing).holding) == 2

    await tw.success("drop ball")

    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        assert len(jacob.make(carryable.Containing).holding) == 1

    await tw.success("hold ball")

    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        assert len(jacob.make(carryable.Containing).holding) == 2


@pytest.mark.asyncio
async def test_put_coin_inside_box_and_then_take_out(caplog):
    caplog.set_level(logging.INFO)
    tw = test.TestWorld()
    await tw.initialize()
    await tw.success("make Coin")
    await tw.success("make Box")

    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        assert len(jacob.make(carryable.Containing).holding) == 2

    await tw.failure("put coin in box")
    await tw.failure("open box")
    await tw.success("drop coin")
    await tw.success("modify capacity 1")
    await tw.success("hold coin")
    await tw.success("put coin in box")

    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        assert len(jacob.make(carryable.Containing).holding) == 1

    await tw.success("look down")

    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        area = world.find_entity_area(jacob)
        assert (
            len(
                session.registrar.find_entity_by_name("Box")
                .make(carryable.Containing)
                .holding
            )
            == 1
        )

    await tw.success("close box")
    await tw.failure("take coin out of box")
    await tw.success("open box")
    await tw.success("take coin out of box")

    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        assert (
            len(
                session.registrar.find_entity_by_name("Box")
                .make(carryable.Containing)
                .holding
            )
            == 0
        )
        assert len(jacob.make(carryable.Containing).holding) == 2


@pytest.mark.asyncio
async def test_put_coin_inside_box_and_then_look_inside(caplog):
    caplog.set_level(logging.INFO)
    tw = test.TestWorld()
    await tw.initialize()
    await tw.success("make Box")
    await tw.success("modify capacity 1")
    await tw.success("close box")
    await tw.success("make Coin")

    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        assert len(jacob.make(carryable.Containing).holding) == 2
        coin = jacob.make(carryable.Containing).holding[1]
        assert "Coin" in coin.props.name

    await tw.failure("put coin in box")
    await tw.success("open box")
    await tw.success("put coin in box")

    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        assert len(jacob.make(carryable.Containing).holding) == 1

    r = await tw.execute("look in box")
    assert isinstance(r, reply.EntitiesObservation)
    assert "Coin" in r.items[0].props.name


@pytest.mark.asyncio
async def test_lock_with_new_key(caplog):
    tw = test.TestWorld()
    await tw.initialize()

    await tw.success("make Box")
    await tw.success("modify capacity 1")
    await tw.success("lock box")

    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        assert len(jacob.make(carryable.Containing).holding) == 2

    await tw.failure("open box")
    await tw.success("unlock box")

    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        assert len(jacob.make(carryable.Containing).holding) == 2

    await tw.success("lock box with key")

    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        assert len(jacob.make(carryable.Containing).holding) == 2

    await tw.success("unlock box")

    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        assert len(jacob.make(carryable.Containing).holding) == 2


@pytest.mark.asyncio
async def test_try_unlock_wrong_key(caplog):
    tw = test.TestWorld()
    await tw.initialize()
    await tw.success("make Box")
    await tw.success("lock box")

    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        assert len(jacob.make(carryable.Containing).holding) == 2

    await tw.success("drop key")

    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        assert len(jacob.make(carryable.Containing).holding) == 1

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
    assert r.entities[0].make(carryable.Carryable).loose
    with tw.domain.session() as session:
        await session.prepare()
        assert session.registrar.find_by_key(r.entities[0].key)


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
