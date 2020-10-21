import pytest
import logging

import props
import entity
import game
import things
import world
import reply
import serializing
import persistence
import test

log = logging.getLogger("dimsum")


@pytest.mark.asyncio
async def test_look_for():
    tw = test.TestWorld()
    await tw.initialize()
    await tw.execute("look for keys")


@pytest.mark.asyncio
async def test_look_empty():
    tw = test.TestWorld()
    await tw.initialize()
    r = await tw.execute("look")
    assert isinstance(r, reply.AreaObservation)
    assert len(r.items) == 0
    assert len(r.living) == 0
    assert len(r.routes) == 0


@pytest.mark.asyncio
async def test_look_items():
    tw = test.TestWorld()
    await tw.initialize()
    await tw.execute("make IPA")
    await tw.execute("drop")
    r = await tw.execute("look")
    assert isinstance(r, reply.AreaObservation)
    assert len(r.items) == 1
    assert len(r.living) == 0


@pytest.mark.asyncio
async def test_look_living():
    tw = test.TestWorld()
    await tw.initialize()
    await tw.add_carla()
    r = await tw.execute("look")
    assert isinstance(r, reply.AreaObservation)
    assert len(r.items) == 0
    assert len(r.living) == 1


@pytest.mark.asyncio
async def test_look_people_invisible():
    tw = test.TestWorld()
    await tw.initialize()
    await tw.add_tomi()
    await tw.add_carla()
    tw.carla.make_invisible()

    r = await tw.execute("look")
    assert isinstance(r, reply.AreaObservation)
    assert len(r.items) == 0
    assert len(r.living) == 1


@pytest.mark.asyncio
async def test_think():
    tw = test.TestWorld()
    await tw.initialize()

    await tw.execute("think")
