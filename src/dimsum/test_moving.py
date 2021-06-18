import logging
import pytest

import game
import movement
import properties
import test
import persistence
import carryable
import entity
import scopes


@pytest.mark.asyncio
async def test_go_unknown():
    tw = test.TestWorld()
    await tw.initialize()

    area_before = tw.world.find_player_area(tw.player)
    await tw.failure("go door")
    area_after = tw.world.find_player_area(tw.player)
    assert area_before == area_after


@pytest.mark.asyncio
async def test_go_adjacent():
    tw = test.TestWorld()
    await tw.initialize()

    another_room = scopes.area(
        creator=tw.world, props=properties.Common("Another Room")
    )

    add_item(
        tw.area,
        scopes.exit(
            area=another_room, creator=tw.world, props=properties.Common("Door")
        ),
    )

    tw.world.add_area(another_room)

    area_before = tw.world.find_player_area(tw.player)
    await tw.success("go door")
    area_after = tw.world.find_player_area(tw.player)
    assert area_after != area_before
    assert area_after == another_room


@pytest.mark.asyncio
async def test_directional_moving_nowhere():
    tw = test.TestWorld()
    await tw.initialize()

    area_before = tw.world.find_player_area(tw.player)
    await tw.failure("go north")
    area_after = tw.world.find_player_area(tw.player)
    assert area_before == area_after


@pytest.mark.asyncio
async def test_directional_moving():
    tw = test.TestWorld()
    await tw.initialize()

    obs = await tw.success("look")
    assert obs

    park = scopes.area(props=properties.Common("North Park"), creator=tw.jacob)

    tw.world.add_area(park)
    add_item(
        tw.area,
        scopes.exit(
            area=park,
            props=properties.Common(name=movement.Direction.NORTH.exiting),
            creator=tw.jacob,
        ),
    )

    area_before = tw.world.find_player_area(tw.player)
    await tw.success("go north")
    area_after = tw.world.find_player_area(tw.player)
    assert area_after != area_before
    assert area_after == park


class Bidirectional:
    def __init__(
        self, there: entity.Entity = None, back: entity.Entity = None, **kwargs
    ):
        assert there
        assert back
        goes_there = scopes.exit(
            area=there,
            props=properties.Common(name="Exit to {0}".format(there.props.name)),
            **kwargs
        )
        comes_back = scopes.exit(
            area=back,
            props=properties.Common(name="Exit to {0}".format(back.props.name)),
            **kwargs
        )
        with back.make(carryable.Containing) as contain:
            contain.add_item(goes_there)
        with there.make(carryable.Containing) as contain:
            contain.add_item(comes_back)


@pytest.mark.asyncio
async def test_programmatic_basic_entrances_and_exits():
    tw = test.TestWorld()

    earth = scopes.area(creator=tw.jacob, props=properties.Common(name="Earth"))
    asteroid = scopes.area(creator=tw.jacob, props=properties.Common(name="Asteroid"))
    Bidirectional(there=asteroid, back=earth, creator=tw.jacob)

    await tw.initialize(earth)

    tw.world.add_area(asteroid)


@pytest.mark.asyncio
async def test_digging_basic():
    tw = test.TestWorld()
    await tw.initialize()

    await tw.success("dig north to 'Kitchen'")
    await tw.success("go #{0}".format(tw.area.props.gid))

    await tw.save("test.sqlite3")


@pytest.mark.asyncio
async def test_digging_with_return():
    tw = test.TestWorld()
    await tw.initialize()

    await tw.success("dig north|south to 'Kitchen'")
    await tw.save("test.sqlite3")
    await tw.success("go north")
    await tw.success("go south")


def add_item(container: entity.Entity, item: entity.Entity):
    with container.make(carryable.Containing) as contain:
        contain.add_item(item)
