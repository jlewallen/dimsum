import pytest

import game
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
async def test_make_door_and_go():
    tw = test.TestWorld()

    await tw.initialize()

    area_before = tw.world.find_player_area(tw.player)
    await tw.execute("make Door")
    await tw.execute("go Door")
    area_after = tw.world.find_player_area(tw.player)
    assert area_after != area_before
