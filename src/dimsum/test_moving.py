from typing import Optional
import pytest

from model import *
import scopes.carryable as carryable
import scopes.movement as movement
import scopes as scopes
import test


@pytest.mark.asyncio
async def test_go_unknown():
    tw = test.TestWorld()
    await tw.initialize()

    area_before: Optional[Entity] = None
    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        area_before = (await find_entity_area(jacob)).key

    await tw.failure("go door")

    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        area_after = (await find_entity_area(jacob)).key
        assert area_before == area_after


@pytest.mark.asyncio
async def test_go_adjacent():
    tw = test.TestWorld()
    await tw.initialize()

    with tw.domain.session() as session:
        world = await session.prepare()

        another_room = scopes.area(creator=session.world, props=Common("Another Room"))

        exit = scopes.exit(
            creator=session.world,
            props=Common("Door"),
            initialize={movement.Exit: dict(area=another_room)},
        )
        await tw.add_item_to_welcome_area(exit, session=session)
        await session.add_area(another_room)
        await session.save()

    area_before = None
    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        area_before = (await find_entity_area(jacob)).key

    await tw.success("go door")

    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        area_after = (await find_entity_area(jacob)).key
        assert area_after != area_before
        assert area_after == another_room.key


@pytest.mark.asyncio
async def test_go_adjacent_two_words():
    tw = test.TestWorld()
    await tw.initialize()

    with tw.domain.session() as session:
        world = await session.prepare()

        another_room = scopes.area(creator=session.world, props=Common("Another Room"))

        exit = scopes.exit(
            creator=session.world,
            props=Common("Old Door"),
            initialize={movement.Exit: dict(area=another_room)},
        )
        await tw.add_item_to_welcome_area(exit, session=session)
        await session.add_area(another_room)
        await session.save()

    area_before = None
    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        area_before = (await find_entity_area(jacob)).key

    await tw.success("go old door")

    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        area_after = (await find_entity_area(jacob)).key
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
        area_before = (await find_entity_area(jacob)).key

    await tw.failure("go north")

    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        area_after = (await find_entity_area(jacob)).key
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
        area = await find_entity_area(jacob)

        park = scopes.area(props=Common("North Park"), creator=world)

        await session.add_area(park)

        exit = scopes.exit(
            creator=world,
            props=Common(name=movement.Direction.NORTH.exiting),
            initialize={movement.Exit: dict(area=park)},
        )

        await tw.add_item_to_welcome_area(exit, session=session)

        area_before = (await find_entity_area(jacob)).key
        await session.save()

    await tw.success("go north")

    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        area_after = (await find_entity_area(jacob)).key
        assert area_after != area_before
        assert area_after == park.key


class Bidirectional:
    def __init__(
        self, there: Optional[Entity] = None, back: Optional[Entity] = None, **kwargs
    ):
        assert there
        assert back
        goes_there = scopes.exit(
            props=Common(name="Exit to {0}".format(there.props.name)),
            initialize={movement.Exit: dict(area=there)},
            **kwargs
        )
        comes_back = scopes.exit(
            props=Common(name="Exit to {0}".format(back.props.name)),
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

        earth = scopes.area(creator=world, props=Common(name="Earth"))
        asteroid = scopes.area(creator=world, props=Common(name="Asteroid"))
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
        wa_key = get_well_known_key(world, WelcomeAreaKey)
        assert wa_key
        area = await session.materialize(key=wa_key)
        gid = area.props.gid

    await tw.success("go #{0}".format(gid))


@pytest.mark.asyncio
async def test_digging_with_return():
    tw = test.TestWorld()
    await tw.initialize()

    await tw.success("dig north|south to 'Kitchen'")
    await tw.success("go north")
    await tw.success("go south")


def add_item(container: Entity, item: Entity):
    with container.make(carryable.Containing) as contain:
        contain.add_item(item)
