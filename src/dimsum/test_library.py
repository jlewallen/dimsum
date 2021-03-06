import logging
import freezegun
import pytest

import domains
import library
import test
from model import *
from test_utils import *


log = logging.getLogger("dimsum")


@pytest.mark.asyncio
@freezegun.freeze_time("2019-09-25")
async def test_library(deterministic, caplog, snapshot):
    tw = test.TestWorld()

    with tw.domain.session() as session:
        world = await session.prepare()

        generics, area = library.create_example_world(world)
        session.register(generics.all)

        await session.add_area(area)
        await session.save()
        assert len(session.registrar.entities) == 60

    with tw.domain.session() as session:
        world = await session.prepare()
        assert len(session.registrar.entities) == 1
        wa_key = get_well_known_key(world, WelcomeAreaKey)
        world = await session.materialize(key=wa_key, reach=domains.infinite_reach)
        assert len(session.registrar.entities) == 59

    await tw.add_jacob()

    with tw.domain.session() as session:
        world = await session.prepare(reach=domains.infinite_reach)
        await session.tick()
        await session.save()

    reloaded = await tw.domain.reload()

    with reloaded.session() as session:
        world = await session.prepare()
        assert len(session.registrar.entities) == 1
        wa_key = get_well_known_key(world, WelcomeAreaKey)
        world = await session.materialize(key=wa_key, reach=domains.infinite_reach)
        assert len(session.registrar.entities) == 63

        await session.tick()
        await session.save()

        assert len(session.registrar.entities) == 63
