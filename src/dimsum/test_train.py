import time
import dataclasses
import pytest
import freezegun
from typing import Dict, List, Optional

from model import *
import scopes.movement as movement
import scopes.carryable as carryable
import scopes.behavior as behavior
import scopes as scopes
import tools
import test
import library
from test_utils import *


@pytest.mark.asyncio
@freezegun.freeze_time("2019-09-25")
async def test_train(snapshot, caplog, deterministic):
    tw = test.TestWorld()
    await tw.initialize()

    with tw.domain.session() as session:
        world = await session.prepare()
        destination = scopes.area(creator=world, props=Common("Wilshire/Western"))
        session.register(destination)

        assert tw.area_key

        stops: List[str] = [tw.area_key, destination.key]

        train = library.Train(
            interior_name="Train Car",
            enter_name="Purple Line Train",
            leave_name="Train Door",
            stops=stops,
        )

        await train.create(session)

        await session.save()

    with freezegun.freeze_time() as frozen_datetime:
        snapshot.assert_match(await tw.to_json(), "1_created.json")

        await tw.success("go train")

        snapshot.assert_match(await tw.to_json(), "2_waiting.json")

        with tw.domain.session() as session:
            await session.tick(0)
            await session.save()

        for i in range(0, 10):
            frozen_datetime.tick()
            with tw.domain.session() as session:
                world = await session.prepare()
                await session.service(time.time())
                await session.save()

        snapshot.assert_match(await tw.to_json(), "3_departed.json")

        await tw.success("go door")

        snapshot.assert_match(await tw.to_json(), "4_arrived.json")

        with tw.domain.session() as session:
            await session.tick(0)
            await session.save()

        await tw.success("go train")

        for i in range(0, 10):
            frozen_datetime.tick()
            with tw.domain.session() as session:
                world = await session.prepare()
                await session.service(time.time())
                await session.save()

        await tw.success("go door")

        snapshot.assert_match(await tw.to_json(), "5_back.json")
