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
    await tw.domain.tick()

    await tw.domain.tick()

    reloaded = await tw.domain.reload()

    await reloaded.tick()

    assert len(reloaded.registrar.entities) == 64
