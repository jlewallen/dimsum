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

    db = persistence.SqliteDatabase()
    await db.open("test.sqlite3")
    await db.purge()
    await db.save(tw.world)

    empty = world.World(tw.bus, context_factory=None)
    await db.load(empty)
    await db.save(empty)

    assert await db.number_of_entities() == 21
