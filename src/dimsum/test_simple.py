import pytest

from model import *
from loggers import get_logger
import scopes.carryable as carryable
import scopes.health as health
import scopes.mechanics as mechanics
import scopes.ownership as ownership
import test

log = get_logger("dimsum")


@pytest.mark.asyncio
async def test_world_owns_itself(caplog):
    whatever = test.create_empty_world()
    with whatever.make(ownership.Ownership) as props:
        assert isinstance(props.owner, World)


@pytest.mark.asyncio
async def test_recipe_simple():
    tw = test.TestWorld()
    await tw.initialize()
    await tw.success("make IPA")
    await tw.success("modify alcohol 100")

    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        with jacob.make(carryable.Containing) as pockets:
            with pockets.holding[0].make(health.Edible) as edible:
                assert edible.nutrition.properties["alcohol"] == 100

        assert len(jacob.make(mechanics.Memory).memory.keys()) == 0

    await tw.success("call this Fancy IPA")

    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        assert len(jacob.make(mechanics.Memory).memory.keys()) == 1

    await tw.success("make fancy")

    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        with jacob.make(carryable.Containing) as pockets:
            assert len(pockets.holding) == 1

    await tw.close()


@pytest.mark.asyncio
async def test_freezing_simple():
    tw = test.TestWorld()
    await tw.initialize()
    await tw.success("make Box")

    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        with jacob.make(carryable.Containing) as pockets:
            assert len(pockets.holding) == 1

    await tw.failure("unfreeze box")
    await tw.success("freeze box")
    await tw.failure("modify name Ignored Box")
    await tw.success("unfreeze box")
    await tw.success("modify name New Box")
    await tw.close()


@pytest.mark.asyncio
async def test_freezing_others_unable_unfreeze():
    tw = test.TestWorld()
    await tw.initialize()
    carla = await tw.add_carla()
    await tw.success("make Box")

    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        with jacob.make(carryable.Containing) as pockets:
            assert len(pockets.holding) == 1

    await tw.failure("unfreeze box")
    await tw.success("freeze box")
    await tw.success("drop")
    await tw.success("hold box", person=tw.carla_key)
    await tw.failure("modify name Ignored Box")
    await tw.failure("unfreeze box")
    await tw.close()


@pytest.mark.asyncio
async def test_lookup_by_object_number():
    tw = test.TestWorld()
    await tw.initialize()
    await tw.failure("freeze #4")
    await tw.success("make Box")
    await tw.success("freeze #4")
    await tw.close()
