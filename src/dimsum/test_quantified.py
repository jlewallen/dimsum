import logging
import pytest

import finders
from model import *
import scopes.carryable as carryable
import scopes.mechanics as mechanics
import test

log = logging.getLogger("dimsum")


@pytest.mark.asyncio
async def test_quantified_drop_partial_and_hold():
    tw = test.TestWorld()

    await tw.initialize()
    await tw.success("make 20 Coin")

    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        area = await find_entity_area(jacob)
        assert len(jacob.make(carryable.Containing).holding) == 1
        assert len(area.make(carryable.Containing).holding) == 0
        assert len(session.registrar.entities) == 4

    await tw.success("drop 5 coin")

    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        area = await find_entity_area(jacob)
        assert len(jacob.make(carryable.Containing).holding) == 1
        assert len(area.make(carryable.Containing).holding) == 1
        assert (
            jacob.make(carryable.Containing)
            .holding[0]
            .make(carryable.Carryable)
            .quantity
            == 15
        )
        assert (
            area.make(carryable.Containing)
            .entities()[0]
            .make(carryable.Carryable)
            .quantity
            == 5
        )
        assert (
            jacob.make(carryable.Containing).holding[0].key
            in session.registrar.entities
        )  # Meh
        assert len(session.registrar.entities) == 5

    await tw.success("hold coin")

    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        area = await find_entity_area(jacob)
        assert len(jacob.make(carryable.Containing).holding) == 1
        assert len(area.make(carryable.Containing).holding) == 0
        assert len(session.registrar.undestroyed) == 4

    await tw.success("drop 5 coin")

    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        area = await find_entity_area(jacob)
        assert len(jacob.make(carryable.Containing).holding) == 1
        assert len(area.make(carryable.Containing).holding) == 1
        assert len(session.registrar.undestroyed) == 5

    await tw.success("drop 5 coin")

    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        area = await find_entity_area(jacob)
        assert len(jacob.make(carryable.Containing).holding) == 1
        assert len(area.make(carryable.Containing).holding) == 1
        assert (
            jacob.make(carryable.Containing)
            .holding[0]
            .make(carryable.Carryable)
            .quantity
            == 10
        )
        assert (
            area.make(carryable.Containing)
            .entities()[0]
            .make(carryable.Carryable)
            .quantity
            == 10
        )
        assert len(session.registrar.undestroyed) == 5


@pytest.mark.asyncio
async def test_quantified_hold_number():
    tw = test.TestWorld()

    await tw.initialize()
    await tw.success("make 20 Coin")
    await tw.success("drop 20 coin")

    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        area = await find_entity_area(jacob)
        assert len(jacob.make(carryable.Containing).holding) == 0
        assert len(area.make(carryable.Containing).holding) == 1

    await tw.success("hold 10 coin")

    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        area = await find_entity_area(jacob)
        assert len(jacob.make(carryable.Containing).holding) == 1
        assert len(area.make(carryable.Containing).holding) == 1


@pytest.mark.asyncio
async def test_quantified_drop_all():
    tw = test.TestWorld()

    await tw.initialize()

    assert await tw.domain.store.number_of_entities() == 3

    await tw.success("make 20 Coin")

    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        area = await find_entity_area(jacob)
        assert len(jacob.make(carryable.Containing).holding) == 1
        assert len(area.make(carryable.Containing).holding) == 0
        assert len(session.registrar.entities) == 4

    await tw.success("drop 20 coin")

    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        area = await find_entity_area(jacob)
        assert len(jacob.make(carryable.Containing).holding) == 0
        assert len(area.make(carryable.Containing).holding) == 1
        assert (
            area.make(carryable.Containing)
            .holding[0]
            .make(carryable.Carryable)
            .quantity
            == 20
        )
        assert len(session.registrar.undestroyed) == 4


@pytest.mark.asyncio
async def test_quantified_drop_inflected():
    tw = test.TestWorld()

    await tw.initialize()

    with tw.domain.session() as session:
        jacob = await session.materialize(key=tw.jacob_key)
        assert len(jacob.make(carryable.Containing).holding) == 0

    await tw.success("make 20 Coin")

    with tw.domain.session() as session:
        jacob = await session.materialize(key=tw.jacob_key)
        assert len(jacob.make(carryable.Containing).holding) == 1

    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        area = await find_entity_area(jacob)
        assert len(area.make(carryable.Containing).holding) == 0

    await tw.success("drop 10 coin")

    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        area = await find_entity_area(jacob)
        assert len(jacob.make(carryable.Containing).holding) == 1
        assert len(area.make(carryable.Containing).holding) == 1


@pytest.mark.asyncio
async def test_quantified_from_recipe_holding_template(caplog):
    tw = test.TestWorld()

    await tw.initialize()
    await tw.success("make Gold Coin")
    await tw.success("call this cash")
    await tw.success("make 4 cash")

    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        area = await find_entity_area(jacob)
        assert len(jacob.make(carryable.Containing).holding) == 1
        assert (
            jacob.make(carryable.Containing)
            .holding[0]
            .make(carryable.Carryable)
            .quantity
            == 5
        )
        assert len(area.make(carryable.Containing).holding) == 0

    await tw.success("look down")

    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        area = await find_entity_area(jacob)
        assert (
            jacob.make(carryable.Containing)
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

    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        item = jacob.make(carryable.Containing).holding[0]
        assert item
        brain = jacob.make(mechanics.Memory)
        assert "r:cash" in brain.memory
        coins = brain.memory["r:cash"]
        assert coins.make(finders.Recipe).template

    await tw.success("obliterate")

    with tw.domain.session() as session:
        jacob = await session.materialize(key=tw.jacob_key)
        assert len(jacob.make(carryable.Containing).holding) == 0

    await tw.success("make 20 cash")

    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        area = await find_entity_area(jacob)
        assert len(jacob.make(carryable.Containing).holding) == 1
        assert len(area.make(carryable.Containing).holding) == 0
        coins = jacob.make(carryable.Containing).holding[0]
        assert coins.make(carryable.Carryable).quantity == 20

    await tw.success("make 20 cash")

    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        area = await find_entity_area(jacob)
        assert len(jacob.make(carryable.Containing).holding) == 1
        assert len(area.make(carryable.Containing).holding) == 0
        assert (
            jacob.make(carryable.Containing)
            .holding[0]
            .make(carryable.Carryable)
            .quantity
            == 40
        )

    await tw.success("look down")

    with tw.domain.session() as session:
        jacob = await session.materialize(key=tw.jacob_key)
        assert (
            jacob.make(carryable.Containing)
            .holding[0]
            .make(carryable.Carryable)
            .quantity
            == 40
        )
