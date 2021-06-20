import pytest
import logging

import model.entity as entity
import model.game as game
import model.world as world
import model.library as library
import model.domains as domains

import serializing
import persistence
import test

log = logging.getLogger("dimsum")


@pytest.mark.asyncio
# @pytest.mark.skip(reason="fix world.everywhere")
async def test_library(caplog):
    tw = test.TestWorld()

    generics, area = library.create_example_world(tw.world)
    tw.registrar.add_entities(generics.all)

    await tw.initialize(area=area)
    await tw.domain.tick()

    db = persistence.SqliteDatabase()
    await db.open("test.sqlite3")
    await db.purge()
    await db.save(tw.registrar)

    await tw.domain.tick()

    empty = domains.Domain()
    await db.load_all(empty.registrar)

    await empty.tick()

    assert await db.number_of_entities() == 65
