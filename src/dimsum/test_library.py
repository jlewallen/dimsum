import pytest
import logging
import freezegun

import model.entity as entity
import model.game as game
import model.world as world
import model.library as library
import model.domains as domains

import serializing
import test

log = logging.getLogger("dimsum")


@pytest.mark.asyncio
@freezegun.freeze_time("2019-09-25")
async def test_library(caplog):
    tw = test.TestWorld()

    with tw.domain.session() as session:
        world = await session.prepare()

        generics, area = library.create_example_world(world)
        session.register(generics.all)

        await session.add_area(area)
        await session.save()
        assert len(session.registrar.entities) == 60  # ?

    with tw.domain.session() as session:
        world = await session.prepare(reach=domains.infinite_reach)
        assert len(session.registrar.entities) == 59

    await tw.add_jacob()

    with tw.domain.session() as session:
        world = await session.prepare(reach=domains.infinite_reach)
        await session.tick()
        await session.tick()
        await session.save()

    reloaded = await tw.domain.reload()

    with reloaded.session() as session:
        assert len(session.registrar.entities) == 0
        await session.prepare(reach=domains.infinite_reach)
        assert len(session.registrar.entities) == 64

        await session.tick()
        await session.save()

        assert len(session.registrar.entities) == 64
