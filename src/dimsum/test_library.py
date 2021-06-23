import pytest
import logging

import model.entity as entity
import model.game as game
import model.world as world
import model.library as library
import model.domains as domains

import serializing
import test

log = logging.getLogger("dimsum")


@pytest.mark.asyncio
async def test_library(caplog):
    tw = test.TestWorld()

    with tw.domain.session() as session:
        world = await session.prepare()

        generics, area = library.create_example_world(session.world)
        tw.domain.registrar.add_entities(generics.all)

        await session.add_area(area)

        await tw.add_jacob()

        await session.tick()
        await session.tick()
        await session.save()

    reloaded = await tw.domain.reload()

    with reloaded.session() as session:
        await session.tick()
        await session.save()

        assert len(session.registrar.entities) == 64
