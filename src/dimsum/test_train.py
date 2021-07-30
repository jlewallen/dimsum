import time
import logging
import dataclasses
import pytest
import freezegun
from datetime import datetime
from typing import Dict, List, Optional

from model import *
from scheduling import Scheduler
from loggers import get_logger
import scopes.movement as movement
import scopes.carryable as carryable
import scopes.behavior as behavior
import scopes as scopes
import tools
import test
import library
from test_utils import *

import library.trains as trains

log = get_logger("dimsum.tests")


@pytest.mark.asyncio
@freezegun.freeze_time("2019-09-25")
async def test_train_factory(snapshot, caplog, deterministic):
    tw = test.TestWorld()
    await tw.initialize()
    assert tw.area_key

    with tw.domain.session() as session:
        world = await session.prepare()

        area = await session.materialize(key=tw.area_key)
        assert area

        stop = scopes.area(creator=world, props=Common("Wilshire/Western"))
        session.register(stop)

        factory = trains.TrainFactory(
            defaults=trains.Defaults(
                interior_name="Train Interior",
                enter_name="Metro Train",
                leave_name="Train Platform",
                stops=[area.key, stop.key],
            )
        )

        with session.ctx() as ctx:
            train = await factory.create(world, ctx)
            tools.hold(area, train)

        await session.save()

    assert await tw.success("look")

    with tw.domain.session() as session:
        await session.prepare()
        scheduler = Scheduler(session)
        await scheduler.service(datetime.now())
        await session.save()

    with freezegun.freeze_time() as frozen_datetime:
        snapshot.assert_match(await tw.to_json(), "1_created.json")

        await tw.success("go train")

        snapshot.assert_match(await tw.to_json(), "2_waiting.json")

        with tw.domain.session() as session:
            await session.prepare()
            scheduler = Scheduler(session)
            future = await scheduler.peek(datetime.max)
            assert future
            frozen_datetime.move_to(future[0].when)
            await scheduler.service(datetime.now())
            await session.save()

        snapshot.assert_match(await tw.to_json(), "3_departed.json")

        await tw.success("go platform")

        snapshot.assert_match(await tw.to_json(), "4_arrived.json")

        await tw.success("go train")

        with tw.domain.session() as session:
            await session.prepare()
            scheduler = Scheduler(session)
            future = await scheduler.peek(datetime.max)
            assert future
            frozen_datetime.move_to(future[0].when)
            await scheduler.service(datetime.now())
            await session.save()

        with tw.domain.session() as session:
            await session.prepare()
            scheduler = Scheduler(session)
            future = await scheduler.peek(datetime.max)
            assert future
            frozen_datetime.move_to(future[0].when)
            await scheduler.service(datetime.now())
            await session.save()

        await tw.success("go platform")

        snapshot.assert_match(await tw.to_json(), "5_back.json")
