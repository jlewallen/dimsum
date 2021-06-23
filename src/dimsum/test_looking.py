import pytest
import logging
import freezegun

import model.game as game
import model.entity as entity
import model.things as things
import model.world as world
import model.reply as reply

import model.scopes.mechanics as mechanics
import model.scopes.carryable as carryable

import serializing

import test

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
    assert len(r.items) == 0
    assert len(r.living) == 1


@pytest.mark.asyncio
async def test_look_people_invisible():
    tw = test.TestWorld()
    await tw.initialize()
    await tw.add_tomi()
    carla = await tw.add_carla()
    with carla.make(mechanics.Visibility) as vis:
        vis.make_invisible()

    r = await tw.success("look")
    assert isinstance(r, reply.AreaObservation)
    assert len(r.items) == 0
    assert len(r.living) == 1


@pytest.mark.asyncio
async def test_think():
    tw = test.TestWorld()
    await tw.initialize()

    await tw.success("think")


@pytest.mark.asyncio
async def test_making_item_hard_to_see(caplog):
    caplog.set_level(logging.INFO)
    tw = test.TestWorld()
    await tw.initialize()
    await tw.add_carla()
    await tw.success("make Box")
    await tw.success("drop")
    assert len(tw.area.make(carryable.Containing).holding) == 1
    r = await tw.success("look")
    assert len(r.items) == 1

    await tw.success("make Orb")
    assert len(tw.player.make(carryable.Containing).holding) == 1
    await tw.success("modify hard to see")
    await tw.success("drop")
    assert len(tw.area.make(carryable.Containing).holding) == 2
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
