import pytest
import logging

import entity
import game
import things
import world
import reply
import serializing
import persistence
import library
import test

log = logging.getLogger("dimsum")


@pytest.mark.asyncio
async def test_area_weather_blows_small_items():
    tw = test.TestWorld()

    generics, area = library.create_example_world(tw.world)
    await tw.initialize(area=area)

    assert await tw.success("go rocky")

    await tw.world.tick(1)
