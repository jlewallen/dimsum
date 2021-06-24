import logging
import pytest

import model.game as game
import model.entity as entity
import model.properties as properties

import model.scopes.carryable as carryable
import model.scopes.movement as movement
import model.scopes as scopes

import test


@pytest.mark.asyncio
async def test_go_unknown():
    tw = test.TestWorld()
    await tw.initialize()

    area_before = None
    with tw.domain.session() as session:
        await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        area_before = session.world.find_player_area(jacob).key

    await tw.failure("go door")

    with tw.domain.session() as session:
        await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        area_after = session.world.find_player_area(jacob).key
        assert area_before == area_after


@pytest.mark.asyncio
async def test_go_adjacent():
    tw = test.TestWorld()
    await tw.initialize()

    with tw.domain.session() as session:
        world = await session.prepare()

        another_room = scopes.area(
            creator=session.world, props=properties.Common("Another Room")
        )

        exit = scopes.exit(
            creator=session.world,
            props=properties.Common("Door"),
            initialize={movement.Exit: dict(area=another_room)},
        )
        add_item(world.welcome_area(), exit)
        await session.add_area(another_room)
        session.register(exit)
        await session.save()

    area_before = None
    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        area_before = session.world.find_player_area(jacob).key

    await tw.success("go door")

    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        area_after = session.world.find_player_area(jacob).key
        assert area_after != area_before
        assert area_after == another_room.key


@pytest.mark.asyncio
async def test_directional_moving_nowhere():
    tw = test.TestWorld()
    await tw.initialize()

    area_before = None
    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        area_before = session.world.find_player_area(jacob).key

    await tw.failure("go north")

    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        area_after = session.world.find_player_area(jacob).key
        assert area_before == area_after


@pytest.mark.asyncio
async def test_directional_moving():
    tw = test.TestWorld()
    await tw.initialize()

    await tw.success("look")

    area_before = None
    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        area = world.find_entity_area(jacob)

        park = scopes.area(props=properties.Common("North Park"), creator=world)

        await session.add_area(park)

        exit = scopes.exit(
            creator=world,
            props=properties.Common(name=movement.Direction.NORTH.exiting),
            initialize={movement.Exit: dict(area=park)},
        )
        add_item(world.welcome_area(), exit)
        session.register(exit)

        area_before = session.world.find_player_area(jacob).key
        await session.save()

    await tw.success("go north")

    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        area_after = session.world.find_player_area(jacob).key
        assert area_after != area_before
        assert area_after == park.key


class Bidirectional:
    def __init__(
        self, there: entity.Entity = None, back: entity.Entity = None, **kwargs
    ):
        assert there
        assert back
        goes_there = scopes.exit(
            props=properties.Common(name="Exit to {0}".format(there.props.name)),
            initialize={movement.Exit: dict(area=there)},
            **kwargs
        )
        comes_back = scopes.exit(
            props=properties.Common(name="Exit to {0}".format(back.props.name)),
            initialize={movement.Exit: dict(area=back)},
            **kwargs
        )
        with back.make(carryable.Containing) as contain:
            contain.add_item(goes_there)
        with there.make(carryable.Containing) as contain:
            contain.add_item(comes_back)


@pytest.mark.asyncio
async def test_programmatic_basic_entrances_and_exits():
    tw = test.TestWorld()

    await tw.initialize()

    with tw.domain.session() as session:
        world = await session.prepare()

        earth = scopes.area(creator=world, props=properties.Common(name="Earth"))
        asteroid = scopes.area(creator=world, props=properties.Common(name="Asteroid"))
        Bidirectional(there=asteroid, back=earth, creator=world)

        await session.add_area(asteroid)


@pytest.mark.asyncio
async def test_digging_basic():
    tw = test.TestWorld()
    await tw.initialize()

    await tw.success("dig north to 'Kitchen'")

    gid = None
    with tw.domain.session() as session:
        world = await session.prepare()
        gid = world.welcome_area().props.gid

    await tw.success("go #{0}".format(gid))


@pytest.mark.asyncio
async def test_digging_with_return():
    tw = test.TestWorld()
    await tw.initialize()

    await tw.success("dig north|south to 'Kitchen'")
    await tw.success("go north")
    await tw.success("go south")


def add_item(container: entity.Entity, item: entity.Entity):
    with container.make(carryable.Containing) as contain:
        contain.add_item(item)
