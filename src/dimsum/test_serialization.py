import pytest
import logging

import properties
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

import ownership

log = logging.getLogger("dimsum")


@pytest.mark.asyncio
async def test_serialize_empty_world(caplog):
    before = test.create_empty_world()
    json = serializing.all(before)

    assert len(json.items()) == 1

    after = test.create_empty_world()
    serializing.restore(after, json)

    assert len(after.entities.items()) == 1


@pytest.mark.asyncio
async def test_serialize_world_one_area(caplog):
    world = test.create_empty_world()
    world.add_area(envo.Area(creator=world, props=properties.Common("Area")))

    json = serializing.all(world)

    assert len(json.items()) == 2

    after = test.create_empty_world()
    serializing.restore(after, json)

    assert len(after.entities.items()) == 2


@pytest.mark.asyncio
async def test_serialize_world_one_item(caplog):
    caplog.set_level(logging.INFO)
    world = test.create_empty_world()
    area = envo.Area(creator=world, props=properties.Common("Area"))
    area.add_item(things.Item(creator=world, props=properties.Common("Item")))
    world.add_area(area)

    assert isinstance(area.holding[0], things.Item)

    json = serializing.all(world)

    assert len(json.items()) == 3

    after = test.create_empty_world()
    serializing.restore(after, json)

    assert isinstance(after.find_entity_by_name("Area"), envo.Area)
    assert isinstance(after.find_entity_by_name("Item"), things.Item)

    assert len(after.find_entity_by_name("Area").holding) == 1
    assert isinstance(after.find_entity_by_name("Area").holding[0], things.Item)

    assert len(after.entities.items()) == 3


@pytest.mark.asyncio
async def test_serialize_world_two_areas_linked_via_directional(caplog):
    caplog.set_level(logging.INFO)
    world = test.create_empty_world()

    two = envo.Area(creator=world, props=properties.Common("Two"))
    one = envo.Area(creator=world, props=properties.Common("One"))

    one.add_item(
        envo.Exit(
            area=two,
            props=properties.Common(name=movement.Direction.NORTH.exiting),
            creator=world,
        )
    )

    two.add_item(
        envo.Exit(
            area=one,
            props=properties.Common(name=movement.Direction.SOUTH.exiting),
            creator=world,
        )
    )

    world.add_area(one)

    json = serializing.all(world)

    assert len(json.items()) == 5

    after = test.create_empty_world()
    entities = serializing.restore(after, json)

    one = after.find_entity_by_name("One")
    assert one

    two = after.find_entity_by_name("Two")
    assert two

    assert two in one.adjacent()
    assert one in two.adjacent()

    assert len(after.entities.items()) == 5


@pytest.mark.asyncio
async def test_serialize_world_two_areas_linked_via_items(caplog):
    caplog.set_level(logging.INFO)
    world = test.create_empty_world()

    one = envo.Area(creator=world, props=properties.Common("One"))
    two = envo.Area(creator=world, props=properties.Common("Two"))

    one.add_item(envo.Exit(area=two, creator=world, props=properties.Common("Item")))
    two.add_item(envo.Exit(area=one, creator=world, props=properties.Common("Item")))

    world.add_area(one)

    json = serializing.all(world)

    assert len(json.items()) == 5

    after = test.create_empty_world()
    entities = serializing.restore(after, json)

    one = after.find_entity_by_name("One")
    assert one

    two = after.find_entity_by_name("Two")
    assert two

    assert isinstance(one.holding[0].props.navigable, envo.Area)
    assert isinstance(two.holding[0].props.navigable, envo.Area)

    assert two in one.adjacent()
    assert one in two.adjacent()

    assert len(after.entities.items()) == 5


@pytest.mark.asyncio
async def test_serialize():
    tw = test.TestWorld()
    await tw.initialize()

    tree = tw.add_item(
        things.Item(creator=tw.jacob, props=properties.Common("A Lovely Tree"))
    )
    clearing = tw.add_simple_area_here("Door", "Clearing")
    tree.get_kind("petals")
    tree.link_area(clearing)
    tree.add_behavior(
        "b:test:tick",
        lua="""
function(s, world, area, item)
    debug("ok", area, item, time)
    return area.make({
        kind = item.kind("petals"),
        name = "Flower Petal",
        quantity = 10,
        color = "red",
    })
end
""",
    )

    db = persistence.SqliteDatabase()
    await db.open("test.sqlite3")
    await db.purge()
    await db.save(tw.world)

    empty = world.World(tw.bus, context_factory=None)
    await db.load(empty)


@pytest.mark.asyncio
async def test_unregister_destroys(caplog):
    caplog.set_level(logging.INFO)
    tw = test.TestWorld()
    await tw.initialize()

    db = persistence.SqliteDatabase()
    await db.open("test.sqlite3")
    await db.purge()

    assert await db.number_of_entities() == 0

    await tw.execute("make Box")
    box = tw.player.holding[0]
    assert not box.props.destroyed
    await db.save(tw.world)

    assert await db.number_of_entities() == 4

    await tw.execute("obliterate")
    assert box.props.destroyed
    await db.save(tw.world)

    assert await db.number_of_entities() == 3

    empty = world.World(tw.bus, context_factory=None)
    await db.load(empty)


@pytest.mark.asyncio
async def test_transients_preserved(caplog):
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
    await tw.realize()
    await tw.success("pour from Keg")
    r = await tw.success("look in mug")
    assert len(r.entities) == 1
    assert "Alai" in r.entities[0].props.name
    assert r.entities[0].loose


@pytest.mark.asyncio
async def test_serialize_library(caplog):
    caplog.set_level(logging.INFO)
    tw = test.TestWorld()
    await tw.initialize()

    generics, area = library.create_example_world(tw.world)
    tw.world.add_area(area)

    json = serializing.serialize(
        {"aras": tw.world.areas()}, unpicklable=False, indent=4
    )

    assert "py/id" not in json


@pytest.mark.asyncio
async def test_serialize_preserves_owner_reference(caplog):
    world = test.create_empty_world()
    world.add_area(envo.Area(creator=world, props=properties.Common("Area")))

    json = serializing.all(world)

    assert len(json.items()) == 2

    after = test.create_empty_world()

    serializing.restore(after, json)

    assert len(after.entities.items()) == 2

    for key, e in after.entities.items():
        with e.make(ownership.Ownership) as props:
            assert isinstance(props.owner, entity.Entity)


@pytest.mark.asyncio
async def test_serialize_properties_directly(caplog):
    world = test.create_empty_world()

    props = properties.Common("Area")

    props.owner = world

    json = serializing.serialize(props)

    log.info(json)


class Example:
    def __init__(self, world: world.World = None):
        self.one = envo.Area(creator=world, props=properties.Common("Area"))
        self.two = self.one


@pytest.mark.asyncio
async def test_serialize_properties_on_entity(caplog):
    world = test.create_empty_world()

    area = envo.Area(creator=world, props=properties.Common("Area"))
    area.owner = world
    area.damn = world

    ex = Example(world)

    json = serializing.serialize(ex, indent=True)

    log.info(json)
