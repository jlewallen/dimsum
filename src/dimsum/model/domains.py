from typing import Optional, List, Sequence, Dict, Union, Any, Literal, Callable, cast

import logging
import dataclasses
import functools
import time

import model.game as game
import model.reply as reply
import model.entity as entity
import model.world as world
import model.tools as tools
import model.events as events

import model.scopes.movement as movement
import model.scopes.carryable as carryable
import model.scopes.occupyable as occupyable
import model.scopes.behavior as behavior
import model.scopes as scopes

import plugins.actions as actions

from bus import EventBus

import context
import serializing
import proxying
import dynamic
import grammars
import storage
import saying

log = logging.getLogger("dimsum.model")
scopes.set_proxy_factory(proxying.create)  # TODO cleanup


def infinite_reach(entity: entity.Entity, depth: int):
    return 0


def default_reach(entity: entity.Entity, depth: int):
    if depth == 3:
        return -1
    if entity.klass == scopes.AreaClass:
        return 1
    return 0


class Session:
    def __init__(
        self,
        store: Optional[storage.EntityStorage] = None,
        handlers: Optional[List[Any]] = None,
        evaluator: Optional[grammars.CommandEvaluator] = None,
    ):
        super().__init__()
        assert store
        assert evaluator
        self.store: storage.EntityStorage = store
        self.world: Optional[world.World] = None
        self.bus = EventBus(handlers=handlers or [])
        self.registrar = entity.Registrar()
        self.evaluator = evaluator

    async def save(self) -> None:
        log.info("saving %s", self.store)
        assert isinstance(self.world, world.World)
        self.world.update_gid(self.registrar.number)
        modified = serializing.modified(self.registrar)
        await self.store.update(modified)

    def __enter__(self) -> "Session":
        return self

    def __exit__(self, type, value, traceback) -> Literal[False]:
        # TODO Warn on unsaved changes?
        return False

    def register(self, entity: entity.Entity) -> entity.Entity:
        return self.registrar.register(entity)

    def unregister(self, entity: entity.Entity) -> entity.Entity:
        return self.registrar.unregister(entity)

    async def try_materialize(
        self,
        key: Optional[str] = None,
        gid: Optional[int] = None,
        json: Optional[List[entity.Serialized]] = None,
        reach=None,
    ) -> serializing.Materialized:
        materialized = await serializing.materialize(
            registrar=self.registrar,
            store=self.store,
            key=key,
            gid=gid,
            json=json,
            reach=reach if reach else default_reach,
            proxy_factory=proxying.create,
        )

        for updated_world in [e for e in materialized.all() if e.key == world.Key]:
            assert isinstance(updated_world, world.World)
            self.world = updated_world

        return materialized

    async def materialize(self, **kwargs) -> entity.Entity:
        materialized = await self.try_materialize(**kwargs)
        return materialized.one()

    async def prepare(self, reach=None):
        if self.world:
            return self.world

        maybe_world = await self.try_materialize(
            key=world.Key, reach=reach if reach else None
        )

        if maybe_world.maybe_one():
            self.world = cast(world.World, maybe_world.one())
            assert isinstance(self.world, world.World)

        if self.world:
            self.registrar.number = self.world.gid()
            return self.world

        log.info("creating new world")
        self.world = world.World()
        self.register(self.world)
        return self.world

    async def execute(self, player: entity.Entity, command: str):
        assert self.world
        log.info("executing: '%s'", command)
        contributing = tools.get_contributing_entities(self.world, player)
        dynamic_behavior = dynamic.Behavior(self.world, contributing)
        evaluators = grammars.PrioritizedEvaluator(
            dynamic_behavior.evaluators + [self.evaluator]
        )
        action = await evaluators.evaluate(command, world=world, player=player)
        assert action
        assert isinstance(action, game.Action)
        return await self.perform(action, player, dynamic_behavior=dynamic_behavior)

    async def perform(
        self,
        action,
        person: Optional[entity.Entity] = None,
        dynamic_behavior: Optional["dynamic.Behavior"] = None,
        **kwargs
    ) -> game.Reply:

        log.info("-" * 100)
        log.info("%s", action)
        log.info("-" * 100)

        await self.prepare()

        assert self.world

        area = self.world.find_entity_area(person) if person else None

        with WorldCtx(person=person, session=self, **kwargs) as ctx:
            try:
                return await action.perform(
                    world=self.world,
                    area=area,
                    person=person,
                    ctx=ctx,
                    dynamic_behavior=dynamic_behavior,
                )
            except entity.EntityFrozen:
                return game.Failure("whoa, that's frozen")

    async def tick(self, now: Optional[float] = None):
        await self.prepare()

        if now is None:
            now = time.time()

        await self.everywhere(world.TickHook, time=now)

        return now

    async def everywhere(self, name: str, **kwargs):
        assert self.world

        log.info("everywhere:%s %s", name, kwargs)
        everything: List[entity.Entity] = []
        with self.world.make(behavior.BehaviorCollection) as world_behaviors:
            everything = world_behaviors.entities
        for entity in everything:
            with entity.make(behavior.Behaviors) as behave:
                if behave.get_default():
                    log.info("everywhere: %s", entity)
                    area = self.world.find_entity_area(entity)
                    assert area
                    with WorldCtx(entity=entity, session=self, **kwargs) as ctx:
                        await ctx.hook(name)

    async def add_area(
        self, area: entity.Entity, depth=0, seen: Optional[Dict[str, str]] = None
    ):
        await self.prepare()

        assert area
        assert self.world

        if seen is None:
            seen = {}

        if area.key in seen:
            return

        occupied = area.make(occupyable.Occupyable).occupied

        with self.world.make(world.Welcoming) as welcoming:
            if welcoming.area:
                existing_occupied = welcoming.area.make(occupyable.Occupyable).occupied
                if len(existing_occupied) < len(occupied):
                    log.info("updating welcome-area")
                    assert area
                    welcoming.area = area
            else:
                log.info("updating welcome-area")
                assert area
                welcoming.area = area

        seen[area.key] = area.key

        log.debug("add-area:%d %s %s", depth, area.key, area)

        self.registrar.register(area)

        for entity in area.make(occupyable.Occupyable).occupied:
            self.registrar.register(entity)

        for entity in area.make(carryable.Containing).holding:
            self.registrar.register(entity)

        for item in area.make(carryable.Containing).holding:
            maybe_area = item.make(movement.Exit).area
            if maybe_area:
                log.debug("linked-via-ex[%s] %s", depth, maybe_area)
                await self.add_area(maybe_area, depth=depth + 1, seen=seen)

            for linked in item.make(movement.Movement).adjacent():
                log.debug("linked-via-item[%d]: %s (%s)", depth, linked, item)
                await self.add_area(linked, depth=depth + 1, seen=seen)

        for linked in area.make(movement.Movement).adjacent():
            log.debug("linked-adj[%d]: %s", depth, linked)
            await self.add_area(linked, depth=depth + 1, seen=seen)

        log.debug("area-done:%d %s", depth, area.key)


class Domain:
    def __init__(
        self,
        store: Optional[storage.EntityStorage] = None,
        handlers: Optional[List[Any]] = None,
        **kwargs
    ):
        super().__init__()
        self.store = store if store else storage.SqliteStorage(":memory:")
        self.handlers = handlers or []
        self.evaluator = grammars.create_static_evaluator()

    def session(self, handlers=None) -> "Session":
        log.info("session:new")
        combined = (handlers or []) + self.handlers
        return Session(
            store=self.store,
            handlers=combined,
            evaluator=self.evaluator,
        )

    async def reload(self):
        return Domain(empty=True, store=self.store)


@dataclasses.dataclass
class HookEvent(events.Event):
    hook: str

    @property
    def name(self) -> str:
        return self.hook


class WorldCtx(context.Ctx):
    def __init__(
        self,
        session: Optional[Session] = None,
        person: Optional[entity.Entity] = None,
        entity: Optional[entity.Entity] = None,
        **kwargs
    ):
        super().__init__()
        assert session and session.world
        self.session = session
        self.world: world.World = session.world
        self.person = person
        self.bus = session.bus
        self.entities: tools.EntitySet = self._get_default_entity_set(entity)

    def _get_default_entity_set(
        self, entity: Optional[entity.Entity]
    ) -> tools.EntitySet:
        assert self.world
        entitySet = tools.EntitySet()
        if self.person:
            entitySet = tools.get_contributing_entities(self.world, self.person)
        else:
            entitySet.add(tools.Relation.WORLD, self.world)
        if entity:
            entitySet.add(tools.Relation.OTHER, entity)
        return entitySet

    def __enter__(self):
        context.set(self)
        return self

    def __exit__(self, type, value, traceback):
        context.set(None)
        return False

    def extend(self, **kwargs) -> "WorldCtx":
        for key, l in kwargs.items():
            log.info("extend '%s' %s", key, l)
            if isinstance(l, list):
                for e in l:
                    self.entities.add(tools.Relation.OTHER, e)
            else:
                self.entities.add(tools.Relation.OTHER, l)
        return self

    def register(self, entity: entity.Entity) -> entity.Entity:
        return self.session.register(entity)

    def unregister(self, destroyed: entity.Entity) -> entity.Entity:
        entity.cleanup(destroyed, world=self.world)
        return self.session.unregister(destroyed)

    async def standard(self, klass, *args, **kwargs):
        assert self.world
        if self.person:
            assert self.person
            area = self.world.find_person_area(self.person)
            a = (self.person, area, []) + args
            await self.publish(klass(*a, **kwargs))

    async def publish(self, *args: events.Event, **kwargs):
        assert self.world
        dynamic_behavior = dynamic.Behavior(self.world, self.entities)
        for arg in args:
            log.info("publish %s entities=%s", arg, self.entities)
            await self.bus.publish(arg)
            await dynamic_behavior.notify(saying.NotifyAll(arg.name, arg, {}))

    async def hook(self, name: str) -> None:
        assert self.world

        await self.publish(HookEvent(name))

    def create_item(
        self, quantity: Optional[float] = None, initialize=None, **kwargs
    ) -> entity.Entity:
        initialize = initialize if initialize else {}
        if quantity:
            initialize = {carryable.Carryable: dict(quantity=quantity)}
        return self.register(scopes.item(initialize=initialize, **kwargs))

    async def find_item(
        self, candidates=None, scopes=[], exclude=None, number=None, **kwargs
    ) -> Optional[entity.Entity]:
        log.info(
            "find-item: gid=%s candidates=%s exclude=%s scopes=%s kw=%s",
            number,
            candidates,
            exclude,
            scopes,
            kwargs,
        )

        if number is not None:
            maybe_by_gid = await self.session.try_materialize(gid=number)
            if maybe_by_gid.empty():
                return None
            return maybe_by_gid.one()

        if len(candidates) == 0:
            return None

        found: Optional[entity.Entity] = None

        for e in candidates:
            if exclude and e in exclude:
                continue

            if scopes:
                has = [e.has(scope) for scope in scopes]
                if len(has) == 0:
                    continue

            if e.describes(**kwargs):
                return e
            else:
                if "q" in kwargs:
                    found = None
                else:
                    found = e

        return found


def flatten(l):
    return [item for sl in l for item in sl]
