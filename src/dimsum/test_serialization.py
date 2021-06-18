import pytest
import logging

import properties
import entity
import game
import things
import world
import movement
import serializing
import persistence
import library
import carryable
import behavior
import scopes
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
    world.add_area(scopes.area(creator=world, props=properties.Common("Area")))

    json = serializing.all(world)

    assert len(json.items()) == 2

    after = test.create_empty_world()
    serializing.restore(after, json)

    assert len(after.entities.items()) == 2


@pytest.mark.asyncio
async def test_serialize_world_one_item(caplog):
    caplog.set_level(logging.INFO)
    world = test.create_empty_world()
    area = scopes.area(creator=world, props=properties.Common("Area"))
    add_item(area, scopes.item(creator=world, props=properties.Common("Item")))
    world.add_area(area)

    assert area.make(carryable.Containing).holding[0]

    json = serializing.all(world)

    assert len(json.items()) == 3

    after = test.create_empty_world()
    serializing.restore(after, json)

    assert after.find_entity_by_name("Area")
    assert after.find_entity_by_name("Item")

    assert (
        len(after.find_entity_by_name("Area").make(carryable.Containing).holding) == 1
    )
    assert after.find_entity_by_name("Area").make(carryable.Containing).holding[0]

    assert len(after.entities.items()) == 3


@pytest.mark.asyncio
async def test_serialize_world_two_areas_linked_via_directional(caplog):
    caplog.set_level(logging.INFO)
    world = test.create_empty_world()

    two = scopes.area(creator=world, props=properties.Common("Two"))
    one = scopes.area(creator=world, props=properties.Common("One"))

    add_item(
        one,
        scopes.exit(
            area=two,
            props=properties.Common(name=movement.Direction.NORTH.exiting),
            creator=world,
        ),
    )

    add_item(
        two,
        scopes.exit(
            area=one,
            props=properties.Common(name=movement.Direction.SOUTH.exiting),
            creator=world,
        ),
    )

    world.add_area(one)

    json = serializing.all(world)

    assert len(json.items()) == 5

    for key, data in json.items():
        log.info("%s", data)

    after = test.create_empty_world()
    entities = serializing.restore(after, json)

    one = after.find_entity_by_name("One")
    assert one

    two = after.find_entity_by_name("Two")
    assert two

    assert two in one.make(movement.Movement).adjacent()
    assert one in two.make(movement.Movement).adjacent()

    assert len(after.entities.items()) == 5


@pytest.mark.asyncio
async def test_serialize_world_two_areas_linked_via_items(caplog):
    world = test.create_empty_world()

    one = scopes.area(creator=world, props=properties.Common("One"))
    two = scopes.area(creator=world, props=properties.Common("Two"))

    add_item(
        one, scopes.exit(area=two, creator=world, props=properties.Common("Item-One"))
    )
    add_item(
        two, scopes.exit(area=one, creator=world, props=properties.Common("Item-Two"))
    )

    assert two in one.make(movement.Movement).adjacent()
    assert one in two.make(movement.Movement).adjacent()

    world.add_area(one)

    json = serializing.all(world, indent=True)

    assert len(json.items()) == 5

    after = test.create_empty_world()
    entities = serializing.restore(after, json)

    one = after.find_entity_by_name("One")
    assert one

    two = after.find_entity_by_name("Two")
    assert two

    assert one.make(carryable.Containing).holding[0].make(movement.Exit).area
    assert two.make(carryable.Containing).holding[0].make(movement.Exit).area

    assert two in one.make(movement.Movement).adjacent()
    assert one in two.make(movement.Movement).adjacent()

    assert len(after.entities.items()) == 5


@pytest.mark.asyncio
async def test_serialize():
    tw = test.TestWorld()
    await tw.initialize()

    tree = tw.add_item(
        scopes.item(creator=tw.jacob, props=properties.Common("A Lovely Tree"))
    )
    clearing = tw.add_simple_area_here("Door", "Clearing")
    tree.get_kind("petals")
    with tree.make(movement.Movement) as nav:
        nav.link_area(clearing)

    with tree.make(behavior.Behaviors) as behave:
        behave.add_behavior(
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
    tw = test.TestWorld()
    await tw.initialize()

    db = persistence.SqliteDatabase()
    await db.open("test.sqlite3")
    await db.purge()

    assert await db.number_of_entities() == 0

    await tw.execute("make Box")
    box = tw.player.make(carryable.Containing).holding[0]
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
    assert r.entities[0].make(carryable.Carryable).loose


@pytest.mark.asyncio
async def test_serialize_library(caplog):
    tw = test.TestWorld()
    await tw.initialize()

    generics, area = library.create_example_world(tw.world)
    tw.world.add_area(area)

    json = serializing.serialize(
        {"entities": tw.world.entities}, unpicklable=False, indent=4
    )

    assert "py/id" not in json


@pytest.mark.asyncio
async def test_serialize_preserves_owner_reference(caplog):
    world = test.create_empty_world()
    world.add_area(scopes.area(creator=world, props=properties.Common("Area")))

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
        self.one = scopes.area(creator=world, props=properties.Common("Area"))
        self.two = self.one


@pytest.mark.asyncio
async def test_serialize_properties_on_entity(caplog):
    world = test.create_empty_world()

    area = scopes.area(creator=world, props=properties.Common("Area"))
    area.owner = world
    area.damn = world

    ex = Example(world)

    json = serializing.serialize(ex, indent=True)

    log.info(json)


def add_item(container: entity.Entity, item: entity.Entity):
    with container.make(carryable.Containing) as contain:
        contain.add_item(item)
