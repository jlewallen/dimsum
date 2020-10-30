import logging
import pytest

import game
import envo
import movement
import props
import test


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

    door_room = tw.add_simple_area_here("Door", "Door Room")

    area_before = tw.world.find_player_area(tw.player)
    await tw.success("go door")
    area_after = tw.world.find_player_area(tw.player)
    assert area_after != area_before
    assert area_after == door_room


@pytest.mark.asyncio
async def test_make_door_and_go_and_get_the_fuck_back():
    tw = test.TestWorld()
    await tw.initialize()

    await tw.success("make Door")

    area_before = tw.world.find_player_area(tw.player)

    await tw.success("go Door")
    area_after = tw.world.find_player_area(tw.player)
    assert area_after != area_before

    await tw.success("look down")

    await tw.success("go Door")
    area_after = tw.world.find_player_area(tw.player)
    assert area_after == area_before


@pytest.mark.asyncio
async def test_climb_wall(caplog):
    tw = test.TestWorld()
    await tw.initialize()

    await tw.success("make Wall")

    area_before = tw.world.find_player_area(tw.player)

    await tw.success("climb wall")
    area_after = tw.world.find_player_area(tw.player)
    assert area_after != area_before

    await tw.success("look")

    await tw.success("climb wall")
    area_after = tw.world.find_player_area(tw.player)
    assert area_after == area_before


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

    park = envo.Area(details=props.Details("North Park"))

    tw.world.add_area(park)
    tw.area.add_route(
        movement.DirectionalRoute(direction=movement.Direction.NORTH, area=park)
    )

    area_before = tw.world.find_player_area(tw.player)
    await tw.success("go north")
    area_after = tw.world.find_player_area(tw.player)
    assert area_after != area_before
    assert area_after == park
