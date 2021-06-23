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

    generics, area = library.create_example_world(tw.world)
    tw.registrar.add_entities(generics.all)

    await tw.initialize(area=area)
    with tw.domain.session() as session:
        await session.tick()

        await session.tick()

    reloaded = await tw.domain.reload()

    with reloaded.session() as session:
        await session.tick()

        assert len(session.registrar.entities) == 64
