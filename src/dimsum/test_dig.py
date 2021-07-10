import logging
import pytest

import test

log = logging.getLogger("dimsum")


@pytest.mark.asyncio
async def test_dig_north_no_quotes():
    tw = test.TestWorld()
    await tw.initialize()
    await tw.success("dig north to Canada")
    await tw.success("go north")


@pytest.mark.asyncio
async def test_dig_north_single_quotes():
    tw = test.TestWorld()
    await tw.initialize()
    await tw.success("dig north to 'Canada'")
    await tw.success("go north")


@pytest.mark.asyncio
async def test_dig_north_double_quotes():
    tw = test.TestWorld()
    await tw.initialize()
    await tw.success('dig north to "Canada"')
    await tw.success("go north")


@pytest.mark.asyncio
async def test_dig_door_and_go_and_get_the_fuck_back():
    tw = test.TestWorld()
    await tw.initialize()

    await tw.success("dig Door|Door to 'Kitchen'")

    area_before = None
    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        area_before = world.find_person_area(jacob).key

    await tw.success("go Door")

    area_area = None
    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        area_after = world.find_person_area(jacob).key

    assert area_after != area_before

    await tw.success("look down")

    await tw.success("go Door")

    area_after = None
    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        area_after = world.find_person_area(jacob).key

    assert area_after == area_before


@pytest.mark.asyncio
@pytest.mark.skip(reason="custom movement verb 'climb'")
async def test_dig_wall_and_climb_wall(caplog):
    tw = test.TestWorld()
    await tw.initialize()

    await tw.success("dig Wall|Wall to 'A High Ledge'")

    area_before = None
    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        area_before = world.find_person_area(jacob).key

    await tw.success("climb wall")

    area_after = None
    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        area_after = world.find_person_area(jacob).key

    assert area_after != area_before

    await tw.success("look")

    await tw.success("climb wall")

    area_after = None
    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        area_after = world.find_person_area(jacob).key

    assert area_after == area_before
