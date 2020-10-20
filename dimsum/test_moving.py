import logging
import pytest

import game
import movement
import props
import test


@pytest.mark.asyncio
async def test_go_unknown():
    tw = test.TestWorld()

    await tw.initialize()

    area_before = tw.world.find_player_area(tw.player)
    await tw.execute("go door")
    area_after = tw.world.find_player_area(tw.player)
    assert area_before == area_after


@pytest.mark.asyncio
async def test_go_adjacent():
    tw = test.TestWorld()
    door_room = tw.add_simple_area_here("Door", "Door Room")

    await tw.initialize()

    area_before = tw.world.find_player_area(tw.player)
    await tw.execute("go door")
    area_after = tw.world.find_player_area(tw.player)
    assert area_after != area_before
    assert area_after == door_room


@pytest.mark.asyncio
async def test_make_door_and_go_and_get_the_fuck_back():
    tw = test.TestWorld()

    await tw.initialize()

    await tw.execute("make Door")

    area_before = tw.world.find_player_area(tw.player)

    await tw.execute("go Door")
    area_after = tw.world.find_player_area(tw.player)
    assert area_after != area_before

    await tw.execute("look down")

    await tw.execute("go Door")
    area_after = tw.world.find_player_area(tw.player)
    assert area_after == area_before


@pytest.mark.asyncio
async def test_climb_wall(caplog):
    caplog.set_level(logging.INFO)
    tw = test.TestWorld()

    await tw.initialize()

    await tw.execute("make Wall")

    area_before = tw.world.find_player_area(tw.player)

    await tw.execute("climb wall")
    area_after = tw.world.find_player_area(tw.player)
    assert area_after != area_before

    await tw.execute("look")

    await tw.execute("climb wall")
    area_after = tw.world.find_player_area(tw.player)
    assert area_after == area_before


@pytest.mark.asyncio
async def test_directional_moving_nowhere():
    tw = test.TestWorld()

    await tw.initialize()

    area_before = tw.world.find_player_area(tw.player)
    await tw.execute("go north")
    area_after = tw.world.find_player_area(tw.player)
    assert area_before == area_after


@pytest.mark.asyncio
async def test_directional_moving():
    tw = test.TestWorld()

    await tw.initialize()

    obs = await tw.execute("look")
    assert obs

    park = game.Area(details=props.Details("North Park"))

    tw.world.add_area(park)
    tw.area.add_route(
        movement.DirectionalRoute(direction=movement.Direction.NORTH, area=park)
    )

    area_before = tw.world.find_player_area(tw.player)
    await tw.execute("go north")
    area_after = tw.world.find_player_area(tw.player)
    assert area_after != area_before
    assert area_after == park