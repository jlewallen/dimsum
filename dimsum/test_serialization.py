import pytest
import logging

import props
import entity
import game
import envo
import things
import world
import movement
import serializing
import persistence
import library
import test

log = logging.getLogger("dimsum")


@pytest.mark.asyncio
async def test_serialize_empty_world(caplog):
    before = test.create_empty_world()
    json = serializing.all(before)

    assert len(json.items()) == 0

    after = test.create_empty_world()
    serializing.restore(after, json)

    assert len(after.entities.items()) == 0


@pytest.mark.asyncio
async def test_serialize_world_one_area(caplog):
    world = test.create_empty_world()
    world.add_area(envo.Area(creator=world, details=props.Details("Area")))

    json = serializing.all(world)

    assert len(json.items()) == 1

    after = test.create_empty_world()
    serializing.restore(after, json)

    assert len(after.entities.items()) == 1


@pytest.mark.asyncio
async def test_serialize_world_one_item(caplog):
    caplog.set_level(logging.INFO)
    world = test.create_empty_world()
    area = envo.Area(creator=world, details=props.Details("Area"))
    area.add_item(things.Item(creator=world, details=props.Details("Item")))
    world.add_area(area)

    assert isinstance(area.holding[0], things.Item)

    json = serializing.all(world)

    assert len(json.items()) == 2

    after = test.create_empty_world()
    serializing.restore(after, json)

    assert isinstance(after.find_entity_by_name("Area"), envo.Area)
    assert isinstance(after.find_entity_by_name("Item"), things.Item)

    assert len(after.find_entity_by_name("Area").holding) == 1
    assert isinstance(after.find_entity_by_name("Area").holding[0], things.Item)

    assert len(after.entities.items()) == 2


@pytest.mark.asyncio
async def test_serialize_world_two_areas_linked_via_directional(caplog):
    caplog.set_level(logging.INFO)
    world = test.create_empty_world()

    two = envo.Area(creator=world, details=props.Details("Two"))
    one = envo.Area(creator=world, details=props.Details("One"))
    one.add_route(
        movement.DirectionalRoute(direction=movement.Direction.NORTH, area=two)
    )
    two.add_route(
        movement.DirectionalRoute(direction=movement.Direction.SOUTH, area=one)
    )
    world.add_area(one)

    json = serializing.all(world)

    assert len(json.items()) == 2

    after = test.create_empty_world()
    entities = serializing.restore(after, json)

    one = after.find_entity_by_name("One")
    assert one

    two = after.find_entity_by_name("Two")
    assert two

    assert two in one.adjacent()
    assert one in two.adjacent()

    assert len(after.entities.items()) == 2


@pytest.mark.asyncio
async def test_serialize_world_two_areas_linked_via_items(caplog):
    caplog.set_level(logging.INFO)
    world = test.create_empty_world()

    other = envo.Area(creator=world, details=props.Details("Two"))
    door = things.Item(creator=world, details=props.Details("Item"))
    door.link_area(other)

    area = envo.Area(creator=world, details=props.Details("One"))
    area.add_item_and_link_back(door)
    world.add_area(area)

    json = serializing.all(world)

    assert len(json.items()) == 4

    after = test.create_empty_world()
    entities = serializing.restore(after, json)

    one = after.find_entity_by_name("One")
    assert one

    two = after.find_entity_by_name("Two")
    assert two

    assert len(one.holding[0].routes) == 1
    assert len(two.holding[0].routes) == 1

    assert isinstance(one.holding[0].routes[0].area, envo.Area)
    assert isinstance(two.holding[0].routes[0].area, envo.Area)

    assert two in one.adjacent()
    assert one in two.adjacent()

    assert len(after.entities.items()) == 4
