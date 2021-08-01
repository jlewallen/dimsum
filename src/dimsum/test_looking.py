import freezegun
import pytest
from typing import Optional, List

import tools
from model import *
from domains import Session
from plugins.looking import *
import scopes.carryable as carryable
import scopes.mechanics as mechanics
import test


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
    assert isinstance(r, AreaObservation)
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
    assert isinstance(r, AreaObservation)
    assert len(r.items) == 1
    assert len(r.living) == 0


@pytest.mark.asyncio
async def test_look_living():
    tw = test.TestWorld()
    await tw.initialize()
    await tw.add_carla()
    r = await tw.success("look")
    assert isinstance(r, AreaObservation)

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
        tools.hide(carla)
        await session.save()

    r = await tw.success("look")
    assert isinstance(r, AreaObservation)
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
        area = await find_entity_area(jacob)
        assert len(area.make(carryable.Containing).holding) == 1

    r = await tw.success("look")

    assert len(r.items) == 1

    await tw.success("make Orb")

    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        area = await find_entity_area(jacob)
        assert len(jacob.make(carryable.Containing).holding) == 1

    await tw.success("modify hard to see")
    await tw.success("drop")

    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        area = await find_entity_area(jacob)
        assert len(area.make(carryable.Containing).holding) == 2

    r = await tw.success("look")
    assert len(r.items) == 1

    orb = None

    with freezegun.freeze_time("2000-01-01 00:00:00"):
        r = await tw.success("look for orb")
        assert len(r.entities) == 1
        orb = r.entities[0]

        r = await tw.success("look")
        assert len(r.items) == 2

    with freezegun.freeze_time("2000-01-01 00:20:00"):
        r = await tw.success("look")
        assert len(r.items) == 2

    with freezegun.freeze_time("2000-01-01 01:01:00"):
        r = await tw.success("look")

        assert len(r.items) == 1


def get_first_item_on_ground(
    key: Optional[str] = None, session: Optional[Session] = None
):
    pass


@pytest.mark.asyncio
@freezegun.freeze_time("2019-09-25")
async def test_changing_presence_to_inline_short(snapshot):
    with test.Deterministic():
        tw = test.TestWorld()
        await tw.initialize()
        await tw.add_carla()
        await tw.success("make Box")
        await tw.success("drop")

        await tw.success("modify presence box inline short")

        snapshot.assert_match(await tw.to_json(), "world.json")

        r = await tw.success("look")

        snapshot.assert_match(test.pretty_json(r.render_tree()), "tree.json")

        assert len(r.items) == 1


@pytest.mark.asyncio
@freezegun.freeze_time("2019-09-25")
async def test_changing_presence_to_inline_long(snapshot):
    with test.Deterministic():
        tw = test.TestWorld()
        await tw.initialize()
        await tw.add_carla()
        await tw.success("make Box")
        await tw.success("drop")

        await tw.success("modify presence box inline long")

        snapshot.assert_match(await tw.to_json(), "world.json")

        r = await tw.success("look")

        snapshot.assert_match(test.pretty_json(r.render_tree()), "tree.json")

        assert len(r.items) == 1
