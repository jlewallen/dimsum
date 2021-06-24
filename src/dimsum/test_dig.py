import pytest
import logging

import model.entity as entity
import model.game as game
import model.things as things
import model.world as world
import model.reply as reply

import serializing

import test

log = logging.getLogger("dimsum")


@pytest.mark.asyncio
async def test_dig_north_no_quotes():
    tw = test.TestWorld()
    await tw.initialize()
    await tw.success("dig north to Canada")


@pytest.mark.asyncio
async def test_dig_north_single_quotes():
    tw = test.TestWorld()
    await tw.initialize()
    await tw.success("dig north to 'Canada'")


@pytest.mark.asyncio
async def test_dig_north_double_quotes():
    tw = test.TestWorld()
    await tw.initialize()
    await tw.success('dig north to "Canada"')


@pytest.mark.asyncio
async def test_dig_door_and_go_and_get_the_fuck_back():
    tw = test.TestWorld()
    await tw.initialize()

    await tw.success("dig Door|Door to 'Kitchen'")

    area_before = None
    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        area_before = world.find_player_area(jacob).key

    await tw.success("go Door")

    area_area = None
    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        area_after = world.find_player_area(jacob).key

    assert area_after != area_before

    await tw.success("look down")

    await tw.success("go Door")

    area_after = None
    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        area_after = session.world.find_player_area(jacob).key

    assert area_after == area_before


@pytest.mark.asyncio
async def test_dig_wall_and_climb_wall(caplog):
    tw = test.TestWorld()
    await tw.initialize()

    await tw.success("dig Wall|Wall to 'A High Ledge'")

    area_before = None
    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        area_before = world.find_player_area(jacob).key

    await tw.success("climb wall")

    area_after = None
    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        area_after = world.find_player_area(jacob).key

    assert area_after != area_before

    await tw.success("look")

    await tw.success("climb wall")

    area_after = None
    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        area_after = world.find_player_area(jacob).key

    assert area_after == area_before
