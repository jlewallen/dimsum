import pytest
import logging

import model.entity as entity
import model.game as game
import model.world as world
import model.library as library

import serializing
import persistence
import test

log = logging.getLogger("dimsum")


@pytest.mark.asyncio
async def test_library(caplog):
    tw = test.TestWorld()

    generics, area = library.create_example_world(tw.world)
    tw.world.add_entities(generics.all)

    await tw.initialize(area=area)
    await tw.world.tick()

    db = persistence.SqliteDatabase()
    await db.open("test.sqlite3")
    await db.purge()
    await db.save(tw.world)

    await tw.world.tick()

    empty = world.World(tw.bus, context_factory=tw.world.context_factory)
    await db.load_all(empty)

    await empty.tick()

    await db.save(empty)

    assert await db.number_of_entities() == 65
