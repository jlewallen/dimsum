import pytest
import logging

import model.entity as entity
import model.game as game
import model.things as things
import model.world as world
import model.reply as reply
import model.library as library

import serializing
import persistence
import test

log = logging.getLogger("dimsum")


@pytest.mark.asyncio
async def test_area_weather_blows_small_items():
    tw = test.TestWorld()

    generics, area = library.create_example_world(tw.world)
    await tw.initialize(area=area)

    assert await tw.success("go rocky")

    await tw.world.tick(1)
