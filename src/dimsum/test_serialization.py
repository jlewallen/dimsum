from typing import Dict, Any, List, Optional

import pytest
import logging

import model.game as game
import model.entity as entity
import model.properties as properties
import model.things as things
import model.world as world
import model.library as library
import model.domains as domains

import model.scopes.movement as movement
import model.scopes.carryable as carryable
import model.scopes.behavior as behavior
import model.scopes.ownership as ownership
import model.scopes as scopes

import serializing
import storage

import test

log = logging.getLogger("dimsum")


@pytest.mark.asyncio
async def test_serialize_empty_world(caplog):
    before = domains.Domain()

    json = None
    with before.session() as session:
        await session.prepare()
        await session.save()

        json = serialize_all(session.registrar)

    assert len(json.items()) == 1

    after = domains.Domain()

    with after.session() as session:
        restore(session.registrar, json)

        assert len(session.registrar.entities.items()) == 1


@pytest.mark.asyncio
async def test_serialize_world_one_area(caplog):
    domain = domains.Domain()

    json = None
    with domain.session() as session:
        world = await session.prepare()
        await session.add_area(
            scopes.area(creator=world, props=properties.Common("Area"))
        )

        json = serialize_all(session.registrar)

    assert len(json.items()) == 2

    after = domains.Domain()
    with after.session() as session:
        restore(session.registrar, json)

        assert len(session.registrar.entities.items()) == 2


@pytest.mark.asyncio
async def test_serialize_world_one_item(caplog):
    domain = domains.Domain()

    json = None
    with domain.session() as session:
        world = await session.prepare()

        area = scopes.area(creator=world, props=properties.Common("Area"))
        add_item(area, scopes.item(creator=world, props=properties.Common("Item")))
        with domain.session() as session:
            await session.add_area(area)

        assert area.make(carryable.Containing).holding[0]

        json = serialize_all(session.registrar)

        assert len(json.items()) == 3

    after = domains.Domain()
    with after.session() as session:
        restore(session.registrar, json)

        assert session.registrar.find_entity_by_name("Area")
        assert session.registrar.find_entity_by_name("Item")

        assert (
            len(
                session.registrar.find_entity_by_name("Area")
                .make(carryable.Containing)
                .holding
            )
            == 1
        )
        assert (
            session.registrar.find_entity_by_name("Area")
            .make(carryable.Containing)
            .holding[0]
        )

        assert len(session.registrar.entities.items()) == 3


@pytest.mark.asyncio
async def test_serialize_world_two_areas_linked_via_directional(caplog):
    domain = domains.Domain()

    json = None
    with domain.session() as session:
        world = await session.prepare()

        two = scopes.area(creator=world, props=properties.Common("Two"))
        one = scopes.area(creator=world, props=properties.Common("One"))

        add_item(
            one,
            scopes.exit(
                props=properties.Common(name=movement.Direction.NORTH.exiting),
                creator=world,
                initialize={movement.Exit: dict(area=two)},
            ),
        )

        add_item(
            two,
            scopes.exit(
                props=properties.Common(name=movement.Direction.SOUTH.exiting),
                creator=world,
                initialize={movement.Exit: dict(area=one)},
            ),
        )

        await session.add_area(one)

        json = serialize_all(session.registrar)

    assert len(json.items()) == 5

    after = domains.Domain()
    with after.session() as session:
        entities = restore(session.registrar, json)

        one = session.registrar.find_entity_by_name("One")
        assert one

        two = session.registrar.find_entity_by_name("Two")
        assert two

        assert two in one.make(movement.Movement).adjacent()
        assert one in two.make(movement.Movement).adjacent()

        assert len(session.registrar.entities.items()) == 5


@pytest.mark.asyncio
async def test_serialize_world_two_areas_linked_via_items(caplog):
    domain = domains.Domain()

    json = None
    with domain.session() as session:
        world = await session.prepare()

        one = scopes.area(creator=world, props=properties.Common("One"))
        two = scopes.area(creator=world, props=properties.Common("Two"))

        add_item(
            one,
            scopes.exit(
                creator=world,
                props=properties.Common("Item-One"),
                initialize={movement.Exit: dict(area=two)},
            ),
        )
        add_item(
            two,
            scopes.exit(
                creator=world,
                props=properties.Common("Item-Two"),
                initialize={movement.Exit: dict(area=one)},
            ),
        )

        assert two in one.make(movement.Movement).adjacent()
        assert one in two.make(movement.Movement).adjacent()

        await session.add_area(one)

        json = serialize_all(session.registrar, indent=True)

    assert len(json.items()) == 5

    after = domains.Domain()
    with after.session() as session:
        entities = restore(session.registrar, json)

        one = session.registrar.find_entity_by_name("One")
        assert one

        two = session.registrar.find_entity_by_name("Two")
        assert two

        assert one.make(carryable.Containing).holding[0].make(movement.Exit).area
        assert two.make(carryable.Containing).holding[0].make(movement.Exit).area

        assert two in one.make(movement.Movement).adjacent()
        assert one in two.make(movement.Movement).adjacent()

        assert len(session.registrar.entities.items()) == 5


@pytest.mark.asyncio
async def test_serialize_after_create():
    tw = test.TestWorld()
    await tw.initialize()

    with tw.domain.session() as session:
        world = await session.prepare()

        tree = tw.add_item_to_welcome_area(
            scopes.item(creator=world, props=properties.Common("A Lovely Tree")),
            session=session,
        )
        clearing = await tw.add_simple_area_here("Door", "Clearing")
        tree.get_kind("petals")
        with tree.make(movement.Movement) as nav:
            nav.link_area(clearing)

        with tree.make(behavior.Behaviors) as behave:
            behave.add_behavior(
                session.world,
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
        await session.save()

    log.info("reloading")
    after = await tw.domain.reload()


@pytest.mark.asyncio
async def test_unregister_destroys(caplog):
    tw = test.TestWorld()
    await tw.initialize()

    await tw.execute("make Box")

    assert await tw.domain.store.number_of_entities() == 4

    await tw.execute("obliterate")

    assert await tw.domain.store.number_of_entities() == 3


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
    await tw.success("pour from Keg")
    r = await tw.success("look in mug")
    assert len(r.entities) == 1
    assert "Alai" in r.entities[0].props.name
    assert r.entities[0].make(carryable.Carryable).loose


@pytest.mark.asyncio
async def test_serialize_library(caplog):
    tw = test.TestWorld()
    await tw.initialize()

    with tw.domain.session() as session:
        world = await session.prepare()

        generics, area = library.create_example_world(world)
        await session.add_area(area)

        json = serializing.serialize(
            {"entities": session.registrar.entities}, unpicklable=False, indent=4
        )

        assert "py/id" not in json


@pytest.mark.asyncio
async def test_serialize_preserves_owner_reference(caplog):
    domain = domains.Domain()

    json = None
    with domain.session() as session:
        await session.add_area(
            scopes.area(creator=session.world, props=properties.Common("Area"))
        )
        await session.save()

        json = serialize_all(session.registrar)

    assert len(json.items()) == 2

    after = domains.Domain()

    with after.session() as session:
        restore(session.registrar, json)

        assert len(session.registrar.entities.items()) == 2

        for key, e in session.registrar.entities.items():
            with e.make(ownership.Ownership) as props:
                assert isinstance(props.owner, entity.Entity)


@pytest.mark.asyncio
async def test_serialize_properties_directly(caplog):
    domain = domains.Domain()
    with domain.session() as session:
        props = properties.Common("Area")
        props.owner = session.world
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


def serialize_all(registrar: entity.Registrar, **kwargs) -> Dict[str, str]:
    return {
        key: serializing.serialize(entity, secure=True, **kwargs)
        for key, entity in registrar.entities.items()
    }


def restore(registrar: entity.Registrar, rows: Dict[str, Any]):
    refs: Dict[str, entity.EntityProxy] = {}

    def reference(ref: entity.EntityRef):
        if ref.key not in refs:
            refs[ref.key] = entity.EntityProxy(ref)
        return refs[ref.key]

    entities: Dict[str, entity.Entity] = {}
    for key in rows.keys():
        e = serializing.deserialize(rows[key], reference)
        assert isinstance(e, entity.Entity)
        registrar.register(e)
        entities[key] = e

    for key, baby_entity in refs.items():
        baby_entity.__wrapped__ = entities[key]  # type: ignore

    return entities
