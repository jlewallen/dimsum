import logging
import pytest

import scopes
import domains
import library
import test
from model import *

log = logging.getLogger("dimsum")


@pytest.mark.asyncio
async def test_materialize_infinite_reach(caplog):
    tw = test.TestWorld()

    with tw.domain.session() as session:
        world = await session.prepare()

        generics, area = library.create_example_world(world)
        session.register(generics.all)

        await session.add_area(area)
        await session.save()

    await tw.add_jacob()

    with tw.domain.session() as session:
        world = await session.prepare()
        await session.tick()
        await session.save()

    reloaded = await tw.domain.reload()

    with reloaded.session() as session:
        assert len(session.registrar.entities) == 0
        world = await session.prepare(reach=domains.infinite_reach)
        assert len(session.registrar.entities) == 1
        wa_key = get_well_known_key(world, WelcomeAreaKey)
        world = await session.materialize(key=wa_key, reach=domains.infinite_reach)

        assert len(session.registrar.entities) == 63

        await session.tick()
        await session.save()

        assert len(session.registrar.entities) == 63


@pytest.mark.asyncio
async def test_materialize_reach_1(caplog):
    tw = test.TestWorld()

    with tw.domain.session() as session:
        world = await session.prepare()

        generics, area = library.create_example_world(world)
        session.register(generics.all)

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
        session.register(generics.all)

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
