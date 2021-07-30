import dataclasses
import time
import pytest
import freezegun
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from model import *
from scheduling import Scheduler
import scopes.behavior as behavior
import scopes.inbox as inbox
import scopes as scopes
import test
from test_utils import *


@dataclasses.dataclass
class PingMessage(Event):
    """Only used in these tests. Must be top level for easier use with
    jsonpickle below."""


@pytest.mark.asyncio
@freezegun.freeze_time("2019-09-25")
async def test_inbox_schedule_local_service(snapshot):
    with test.Deterministic():
        tw = test.TestWorld()
        await tw.initialize()

        hammer_key = await tw.add_behaviored_thing("Hammer", "")

        with tw.domain.session() as session:
            world = await session.prepare()
            hammer = await session.try_materialize_key(hammer_key)
            assert hammer

            post_service = await inbox.create_post_service(session, world)

            await post_service.future(
                datetime.now() + timedelta(seconds=5), hammer, PingMessage()
            )

            await session.save()

        snapshot.assert_match(await tw.to_json(), "world_scheduled.json")

        with tw.domain.session() as session:
            world = await session.prepare()
            scheduler = Scheduler(session)
            with freezegun.freeze_time() as frozen_datetime:
                for i in range(0, 6):
                    frozen_datetime.tick()
                    await scheduler.service(datetime.now())
            await session.save()

        snapshot.assert_match(await tw.to_json(), "world.json")


@pytest.mark.asyncio
@freezegun.freeze_time("2019-09-25")
async def test_inbox_schedule_local_dynamic(snapshot):
    with test.Deterministic():
        tw = test.TestWorld()
        await tw.initialize()

        hammer_key = await tw.add_behaviored_thing(
            "Hammer",
            """
@dataclass
class PingMessage(Event):
    value: str

@ds.language('start: "swing"')
async def swing(this, person, post):
    log.info("swing: %s", this)
    await post.future(time() + 5, this, PingMessage("ping#1"))
    return "whoa, careful there!"

@ds.received(PingMessage)
async def ping(this, ev):
    log.info("pong: %s", ev.value)
    log.info("pong: %s", this)
    log.info("pong: %s", this.props)
    log.info("pong: %s", type(this.props))
    this.props.set('gold', 10)
""",
        )

        await tw.success("hold Hammer")
        await tw.success("swing")

        snapshot.assert_match(await tw.to_json(), "world_scheduled.json")

        with tw.domain.session() as session:
            world = await session.prepare()
            scheduler = Scheduler(session)
            with freezegun.freeze_time() as frozen_datetime:
                for i in range(0, 4):
                    frozen_datetime.tick()
                    await scheduler.service(datetime.now())
                frozen_datetime.tick()
                await scheduler.service(datetime.now())
            await session.save()

        snapshot.assert_match(await tw.to_json(), "world.json")
