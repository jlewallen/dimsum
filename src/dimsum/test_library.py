import pytest
import logging

import props
import entity
import game
import world
import serializing
import persistence
import library
import test

log = logging.getLogger("dimsum")


@pytest.mark.asyncio
async def test_library(caplog):
    caplog.set_level(logging.INFO)
    tw = test.TestWorld()
    await tw.initialize()

    tw.world.add_area(library.create_example_world(tw.world))

    await tw.world.tick()

    db = persistence.SqliteDatabase()
    await db.open("test.sqlite3")
    await db.purge()
    await db.save(tw.world)

    await tw.world.tick()

    empty = world.World(tw.bus, context_factory=tw.world.context_factory)
    await db.load(empty)

    await empty.tick()

    await db.save(empty)

    assert await db.number_of_entities() == 39
