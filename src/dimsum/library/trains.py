import typing as t
import abc
from time import time
from dataclasses import dataclass, field

import tools
from loggers import get_logger
from model import (
    Common,
    Entity,
    World,
    Ctx,
    EntityFactory,
    StandardEvent,
    Scope,
    Failure,
    Success,
    All,
)
from model.events import *
from dynamic import Dynsum, LibraryBehavior

from scopes.carryable import Carryable, Containing
from scopes.behavior import Behaviors
from scopes.movement import Exit
import scopes

log = get_logger("dimsum.train")
ok = Success
fail = Failure

# https://stackoverflow.com/questions/3589311/get-defining-class-of-unbound-method-object-in-python-3/25959545#25959545

# End standard dynamic preamble


@dataclass
class CloseDoors(Event):
    pass


@dataclass
class Arrive(Event):
    pass


@dataclass
class Depart(Event):
    pass


class Train(Scope):
    def __init__(
        self,
        stops: t.Optional[t.List[str]] = None,
        door: t.Optional[str] = None,
        interior: t.Optional[str] = None,
        leaving=False,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.stops = stops if stops else []
        self.door = door if door else None
        self.interior = interior if interior else None
        self.leaving = leaving

    async def get_interior(self, ctx):
        return await ctx.materialize_key(self.interior)

    async def at_stop(self):
        area = tools.area_of(self.ourselves)
        assert area
        return area.key in self.stops

    async def get_stop(self, ctx):
        area = tools.area_of(self.ourselves)
        assert area
        index = 0
        if area.key in self.stops:
            index = self.stops.index(area.key)
        assert index >= 0
        new_stop = self.stops[(index + 1) % len(self.stops)]
        return await ctx.materialize_key(new_stop)

    async def leave_station(self, ctx, new_stop: Entity):
        door = await ctx.materialize_key(self.door)
        tools.set_exit(door, area=new_stop, unavailable="The doors are closed!")
        await tools.move_to_limbo(ctx.world, ctx, self.ourselves)

    async def arrive_station(self, ctx):
        door = await ctx.materialize_key(self.door)
        area = tools.set_exit(door, unavailable=None)
        await tools.move_from_limbo(ctx.world, self.ourselves, area)

    async def create_if_necessary(self) -> bool:
        return len(self.stops) > 0


class TrainBehavior(LibraryBehavior):
    def create(self, ds: Dynsum):
        @ds.cron("*/1 * * * *")
        async def move_train(this, ev, say, ctx, post):
            log.info("move-train:scheduled")
            say.nearby(this, f"{this.props.described} is going to leave!")
            with this.make(Train) as train:
                if not await train.create_if_necessary():
                    log.warning("move-train:disabled")
                    return
                interior = await train.get_interior(ctx)
                say.nearby(interior, f"{this.props.described} doors are closing!")
            await post.future(time() + 5, this, CloseDoors())

        @ds.received(CloseDoors)
        async def close_doors(this, ev, say, ctx, post):
            area = tools.area_of(this)
            with this.make(Train) as train:
                log.info("move-train: area=%s stops=%s", area, train.stops)
                new_stop = await train.get_stop(ctx)
                say.nearby(
                    tools.area_of(this), f"{this.props.described} train just left"
                )
                await train.leave_station(ctx, new_stop)
                await post.future(time() + 5, this, Arrive())

                interior = await train.get_interior(ctx)
                say.nearby(
                    interior,
                    f"{this.props.described} has left the station, hold on!",
                )

        @ds.received(Arrive)
        async def arrive(this, ev, say, ctx, post):
            area = tools.area_of(this)
            with this.make(Train) as train:
                log.info("move-train: area=%s stops=%s", area, train.stops)
                await train.arrive_station(ctx)
                arrived_at = tools.area_of(this)
                assert arrived_at
                say.nearby(arrived_at, f"{this.props.described} just arrived")
                interior = await train.get_interior(ctx)
                say.nearby(
                    interior,
                    f"{this.props.described} has arrived at {arrived_at.props.described}, get out",
                )

        @ds.hooks.enter.hook
        async def only_when_doors_open(resume, person, area):
            log.info("only-when-doors-open: %s", person)
            return await resume(person, area)

        return Train


@dataclass
class Defaults:
    interior_name: str
    enter_name: str
    leave_name: str
    stops: t.List[str] = field(default_factory=list)


@dataclass
class TrainFactory(EntityFactory):
    defaults: Defaults

    async def create(self, world: World, ctx: Ctx) -> Entity:
        first_stop = (
            await ctx.materialize_key(key=self.defaults.stops[0])
            if self.defaults.stops
            else None
        )

        interior = scopes.area(creator=world, props=Common(self.defaults.interior_name))
        leave = scopes.exit(
            creator=world,
            props=Common(self.defaults.leave_name),
            initialize={Exit: dict(area=first_stop)},
        )
        enter = scopes.exit(
            creator=world,
            props=Common(self.defaults.enter_name),
            initialize={
                Exit: dict(area=interior),
                Train: dict(
                    interior=interior.key, door=leave.key, stops=self.defaults.stops
                ),
            },
        )

        with interior.make(Containing) as contains:
            contains.hold(leave)

        with enter.make(Behaviors) as behave:
            behave.add_behavior(
                world,
                python="""
from library.trains import *

ds.behaviors([ TrainBehavior() ])

None
""",
            )

        if first_stop:
            with first_stop.make(Containing) as first_stop_ground:
                if first_stop_ground.contains(enter):
                    return first_stop_ground.discard()
                first_stop_ground.hold(enter)
                first_stop.touch()

        ctx.register(enter)
        ctx.register(leave)
        ctx.register(interior)

        return enter
