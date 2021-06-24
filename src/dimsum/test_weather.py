import pytest
import logging

import model.entity as entity
import model.game as game
import model.things as things
import model.world as world
import model.reply as reply
import model.library as library

import serializing
import test

log = logging.getLogger("dimsum")


@pytest.mark.asyncio
async def test_area_weather_blows_small_items():
    tw = test.TestWorld()

    with tw.domain.session() as session:
        world = await session.prepare()

        generics, area = library.create_example_world(world)
        session.registrar.add_entities(generics.all)

        await session.add_area(area)
        await session.save()

    await tw.add_jacob()

    assert await tw.success("go rocky")

    with tw.domain.session() as session:
        await session.tick(1)
