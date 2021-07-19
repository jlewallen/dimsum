import logging
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
from test_utils import *

log = logging.getLogger("dimsum.tests")


@pytest.mark.asyncio
@freezegun.freeze_time("2019-09-25")
async def test_train(snapshot, caplog, deterministic):
    tw = test.TestWorld()
    await tw.initialize()

    destination_key = await tw.create_behaviored_thing(
        "Wilshire/Western", "", ctor=scopes.area
    )

    train_door_key = await tw.create_behaviored_thing(
        "Train Door", "", ctor=scopes.exit
    )

    inside_train_key = await tw.create_behaviored_thing(
        "Train Car",
        """
""",
        ctor=scopes.area,
    )

    with tw.domain.session() as session:
        world = await session.prepare()

        destination = await session.materialize(key=destination_key)
        train_door = await session.materialize(key=train_door_key)
        with train_door.make(movement.Exit) as exit:
            exit.area = await session.materialize(key=tw.area_key)
            train_door.touch()

        inside_train = await session.materialize(key=inside_train_key)
        with inside_train.make(carryable.Containing) as contains:
            contains.hold(train_door)

        await session.save()

    outside_train_key = await tw.add_behaviored_thing(
        "Train",
        """
class Train(Scope):
    def __init__(self, stops: t.Optional[t.List[str]] = None, door: t.Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        self.stops = stops if stops else ["{0}", "{1}"]
        self.door = door if door else "{2}"

@received(TickEvent)
async def move_train(this, ev, say, area, session):
    with this.make(Train) as train:
        log.info("move-train: area=%s stops=%s", area, train.stops)
        if train.stops:
            index = train.stops.index(area.key)
            if index >= 0:
                new_stop = train.stops[(index + 1) % len(train.stops)]
                door = await session.materialize(key=train.door)
                with door.make(Exit) as exit:
                    exit.area = await session.materialize(key=new_stop)
                    door.touch()
                    log.info("move-train: %s new stop %s", this, exit.area)
                    tools.move(this, exit.area)
                    this.touch()

@hooks.enter.hook
def only_when_doors_open(resume, person, area):
    log.info("only_when_doors_open: %s", person)
    return resume(person, area)
""".format(
            tw.area_key, destination_key, train_door_key
        ),
        ctor=scopes.exit,
    )

    with tw.domain.session() as session:
        world = await session.prepare()
        outside_train = await session.materialize(key=outside_train_key)
        inside_train = await session.materialize(key=inside_train_key)
        with outside_train.make(movement.Exit) as exit:
            exit.area = inside_train
            outside_train.touch()
        await session.save()

    snapshot.assert_match(await tw.to_json(), "1_created.json")

    await tw.success("go train")

    snapshot.assert_match(await tw.to_json(), "2_waiting.json")

    with tw.domain.session() as session:
        await session.tick(0)
        await session.save()

    snapshot.assert_match(await tw.to_json(), "3_departed.json")

    await tw.success("go door")

    snapshot.assert_match(await tw.to_json(), "4_arrived.json")
