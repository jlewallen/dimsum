import logging
import test

import freezegun
import model.reply as reply
import model.scopes.carryable as carryable
import model.scopes.mechanics as mechanics
import pytest

log = logging.getLogger("dimsum")


@pytest.mark.asyncio
async def test_look_for_no_such_thing():
    tw = test.TestWorld()
    await tw.initialize()
    await tw.failure("look for keys")


@pytest.mark.asyncio
async def test_look_empty():
    tw = test.TestWorld()
    await tw.initialize()
    r = await tw.success("look")
    assert isinstance(r, reply.AreaObservation)
    assert len(r.items) == 0
    assert len(r.living) == 0
    assert len(r.routes) == 0


@pytest.mark.asyncio
async def test_look_items():
    tw = test.TestWorld()
    await tw.initialize()
    await tw.success("make IPA")
    await tw.success("drop")
    r = await tw.success("look")
    assert isinstance(r, reply.AreaObservation)
    assert len(r.items) == 1
    assert len(r.living) == 0


@pytest.mark.asyncio
async def test_look_living():
    tw = test.TestWorld()
    await tw.initialize()
    await tw.add_carla()
    r = await tw.success("look")
    assert isinstance(r, reply.AreaObservation)

    r = await tw.success("look")
    assert len(r.items) == 0
    assert len(r.living) == 1


@pytest.mark.asyncio
async def test_look_people_invisible():
    tw = test.TestWorld()
    await tw.initialize()
    await tw.add_tomi()
    await tw.add_carla()

    with tw.domain.session() as session:
        world = await session.prepare()
        carla = await session.materialize(key=tw.carla_key)
        with carla.make(mechanics.Visibility) as vis:
            vis.make_invisible()
        await session.save()

    r = await tw.success("look")
    assert isinstance(r, reply.AreaObservation)
    assert len(r.items) == 0
    assert len(r.living) == 1


@pytest.mark.asyncio
async def test_making_item_hard_to_see():
    tw = test.TestWorld()
    await tw.initialize()
    await tw.add_carla()
    await tw.success("make Box")
    await tw.success("drop")

    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        area = world.find_entity_area(jacob)
        assert len(area.make(carryable.Containing).holding) == 1

    r = await tw.success("look")

    assert len(r.items) == 1

    await tw.success("make Orb")

    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        area = world.find_entity_area(jacob)
        assert len(jacob.make(carryable.Containing).holding) == 1

    await tw.success("modify hard to see")
    await tw.success("drop")

    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        area = world.find_entity_area(jacob)
        assert len(area.make(carryable.Containing).holding) == 2

    r = await tw.success("look")
    assert len(r.items) == 1

    orb = None

    with freezegun.freeze_time("2000-01-01 00:00:00"):
        r = await tw.success("look for orb")
        assert len(r.items) == 1
        orb = r.items[0]

        r = await tw.success("look")
        assert len(r.items) == 2

    with freezegun.freeze_time("2000-01-01 00:20:00"):
        r = await tw.success("look")
        assert len(r.items) == 2

    with freezegun.freeze_time("2000-01-01 01:01:00"):
        r = await tw.success("look")

        log.info(tw.dumps(orb))

        assert len(r.items) == 1


def flatten(l):
    return [item for sl in l for item in sl]
