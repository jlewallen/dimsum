import pytest
import logging

import model.entity as entity
import model.game as game
import model.world as world
import model.library as library
import model.domains as domains
import model.scopes as scopes

import serializing
import test

log = logging.getLogger("dimsum")


@pytest.mark.asyncio
async def test_materialize_infinite_reach(caplog):
    tw = test.TestWorld()

    with tw.domain.session() as session:
        world = await session.prepare()

        generics, area = library.create_example_world(world)
        session.registrar.add_entities(generics.all)

        await session.add_area(area)
        await session.save()

    await tw.add_jacob()

    with tw.domain.session() as session:
        world = await session.prepare()
        await session.tick()
        await session.tick()
        await session.save()

    reloaded = await tw.domain.reload()

    with reloaded.session() as session:
        assert len(session.registrar.entities) == 0
        await session.prepare(reach=domains.infinite_reach)

        await session.tick()
        await session.save()

        assert len(session.registrar.entities) == 64


@pytest.mark.asyncio
async def test_materialize_reach_1(caplog):
    tw = test.TestWorld()

    with tw.domain.session() as session:
        world = await session.prepare()

        generics, area = library.create_example_world(world)
        session.registrar.add_entities(generics.all)

        await session.add_area(area)
        await session.save()

    await tw.add_jacob()

    with tw.domain.session() as session:

        def reach(entity, depth):
            if depth == 1:
                return -1
            return 1

        world = await session.prepare(reach=reach)


@pytest.mark.asyncio
async def test_materialize_reach_by_area_3(caplog):
    caplog.set_level(logging.WARNING)
    tw = test.TestWorld()

    with tw.domain.session() as session:
        world = await session.prepare()

        generics, area = library.create_example_world(world)
        session.registrar.add_entities(generics.all)

        await session.add_area(area)
        await session.save()

    await tw.add_jacob()

    caplog.set_level(logging.INFO)
    with tw.domain.session() as session:

        def reach(entity, depth):
            log.info("%s", entity.klass)
            if depth == 3:
                return -1
            if entity.klass == scopes.AreaClass:
                return 1
            return 0

        world = await session.prepare(reach=reach)
