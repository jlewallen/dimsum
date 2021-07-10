import logging
import time
import contextvars
from typing import Any, cast, Dict, List, Literal, Optional, Union

import dynamic
import grammars
import handlers
import tools
import proxying
import saying
import serializing
import storage
from bus import EventBus, SubscriptionManager
from model import (
    Entity,
    World,
    Registrar,
    Serialized,
    Key,
    Event,
    Action,
    TickEvent,
    EntityFrozen,
    Failure,
    Comms,
    Reply,
    ExtendHooks,
    Welcoming,
    Condition,
    cleanup,
    Ctx,
    context,
)
import scopes.behavior as behavior
import scopes.carryable as carryable
import scopes.movement as movement
import scopes.occupyable as occupyable
import scopes as scopes

log = logging.getLogger("dimsum.model")
active_session: contextvars.ContextVar = contextvars.ContextVar("dimsum:session")
scopes.set_proxy_factory(proxying.create)  # TODO cleanup


def get() -> "Session":
    session = active_session.get()
    assert session
    return session


def infinite_reach(entity: Entity, depth: int):
    return 0


def default_reach(entity: Entity, depth: int):
    if entity.klass == scopes.AreaClass:
        if depth == 3:
            return -1
        return 1
    return 0


class Session:
    def __init__(
        self,
        store: Optional[storage.EntityStorage] = None,
        handlers: Optional[List[Any]] = None,
    ):
        super().__init__()
        assert store
        self.store: storage.EntityStorage = store
        self.world: Optional[World] = None
        self.bus = EventBus(handlers=handlers or [])
        self.registrar = Registrar()

    async def save(self) -> None:
        log.info("saving %s", self.store)
        assert isinstance(self.world, World)
        self.world.update_gid(self.registrar.number)
        for key, mod in self.registrar.modified().items():
            mod.props.described = mod.describe()
        modified = serializing.modified(self.registrar)
        await self.store.update(modified)

    def __enter__(self) -> "Session":
        active_session.set(self)
        return self

    def __exit__(self, type, value, traceback) -> Literal[False]:
        active_session.set(None)
        # TODO Warn on unsaved changes?
        return False

    def register(self, entity: Entity) -> Entity:
        return self.registrar.register(entity)

    def unregister(self, entity: Entity) -> Entity:
        return self.registrar.unregister(entity)

    async def try_materialize(
        self,
        key: Optional[str] = None,
        gid: Optional[int] = None,
        json: Optional[List[Serialized]] = None,
        reach=None,
        refresh=None,
    ) -> serializing.Materialized:
        materialized = await serializing.materialize(
            registrar=self.registrar,
            store=self.store,
            key=key,
            gid=gid,
            json=json,
            reach=reach if reach else default_reach,
            proxy_factory=proxying.create,
            refresh=refresh,
        )

        for updated_world in [e for e in materialized.all() if e.key == Key]:
            assert isinstance(updated_world, World)
            self.world = updated_world

        return materialized

    async def materialize(self, **kwargs) -> Entity:
        materialized = await self.try_materialize(**kwargs)
        return materialized.one()

    async def prepare(self, reach=None):
        if self.world:
            return self.world

        maybe_world = await self.try_materialize(
            key=Key, reach=reach if reach else None
        )

        if maybe_world.maybe_one():
            self.world = cast(World, maybe_world.one())
            assert isinstance(self.world, World)

        if self.world:
            self.registrar.number = self.world.gid()
            return self.world

        log.info("creating new world")
        self.world = World()
        self.register(self.world)
        return self.world

    async def execute(self, player: Entity, command: str):
        assert self.world
        log.info("executing: '%s'", command)
        contributing = tools.get_contributing_entities(self.world, player)
        dynamic_behavior = dynamic.Behavior(self.world, contributing)
        log.info("dynamic-hooks: %s", dynamic_behavior.dynamic_hooks)
        evaluator = grammars.PrioritizedEvaluator(
            [dynamic_behavior.lazy_evaluator] + grammars.create_static_evaluators()
        )
        with ExtendHooks(dynamic_behavior.dynamic_hooks):
            log.info("evaluator: '%s'", evaluator)
            action = await evaluator.evaluate(command, world=self.world, player=player)
            assert action
            assert isinstance(action, Action)
            return await self.perform(action, player)

    async def perform(
        self,
        action,
        person: Optional[Entity] = None,
        dynamic_behavior: Optional["dynamic.Behavior"] = None,
        **kwargs
    ) -> Reply:

        log.info("-" * 100)
        log.info("%s", action)
        log.info("-" * 100)

        world = await self.prepare()

        area = world.find_entity_area(person) if person else None

        with WorldCtx(session=self, person=person, **kwargs) as ctx:
            try:
                reply = await action.perform(
                    world=world,
                    area=area,
                    person=person,
                    ctx=ctx,
                    say=ctx.say,
                )
                await ctx.complete()
                return reply
            except EntityFrozen:
                return Failure("whoa, that's frozen")

    async def tick(self, now: Optional[float] = None):
        await self.prepare()

        if now is None:
            now = time.time()

        await self.everywhere(TickEvent(now))

        return now

    async def everywhere(self, ev: Event, **kwargs):
        assert self.world

        log.info("everywhere:%s %s", ev, kwargs)
        everything: List[Entity] = []
        with self.world.make(behavior.BehaviorCollection) as world_behaviors:
            everything = world_behaviors.entities
        for entity in everything:
            # Materialize from the target entity to ensure we have
            # enough in memory to carry out its behavior.
            await get().materialize(key=entity.key, refresh=True)
            with entity.make(behavior.Behaviors) as behave:
                if behave.get_default():
                    log.info("everywhere: %s", entity)
                    with WorldCtx(session=self, entity=entity, **kwargs) as ctx:
                        await ctx.notify(ev)
                        await ctx.complete()

    async def add_area(
        self, area: Entity, depth=0, seen: Optional[Dict[str, str]] = None
    ):
        await self.prepare()

        assert area
        assert self.world

        if seen is None:
            seen = {}

        if area.key in seen:
            return

        occupied = area.make(occupyable.Occupyable).occupied

        with self.world.make(Welcoming) as welcoming:
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
        subscriptions: Optional[SubscriptionManager] = None,
        **kwargs
    ):
        super().__init__()
        self.store = store if store else storage.SqliteStorage(":memory:")
        self.subscriptions = subscriptions if subscriptions else SubscriptionManager()
        self.comms: Comms = self.subscriptions
        self.handlers = [handlers.create(self.subscriptions)]

    def session(self) -> "Session":
        log.info("session:new")
        return Session(
            store=self.store,
            handlers=self.handlers,
        )

    async def reload(self):
        return Domain(empty=True, store=self.store)


class WorldCtx(Ctx):
    def __init__(
        self,
        session: Optional[Session] = None,
        person: Optional[Entity] = None,
        entity: Optional[Entity] = None,
        **kwargs
    ):
        super().__init__()
        assert session and session.world
        self.session = session
        self.world: World = session.world
        self.person = person
        self.reference = person or entity
        self.bus = session.bus
        self.entities: tools.EntitySet = self._get_default_entity_set(entity)
        self.say = saying.Say()

    def _get_default_entity_set(self, entity: Optional[Entity]) -> tools.EntitySet:
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

    def register(self, entity: Entity) -> Entity:
        return self.session.register(entity)

    def unregister(self, destroyed: Entity) -> Entity:
        cleanup(destroyed, world=self.world)
        return self.session.unregister(destroyed)

    async def standard(self, klass, *args, **kwargs):
        assert self.world
        if self.person:
            assert self.person
            area = self.world.find_person_area(self.person)
            a = (self.person, area, []) + args
            await self.publish(klass(*a, **kwargs))

    async def notify(self, ev: Event, **kwargs):
        assert self.world
        log.info("notify=%s entities=%s", ev, self.entities)
        dynamic_behavior = dynamic.Behavior(self.world, self.entities)
        await dynamic_behavior.notify(saying.NotifyAll(ev.name, ev), say=self.say)

    async def complete(self):
        assert self.reference
        await self.say.publish(self.reference)

    async def publish(self, ev: Event):
        assert self.world
        await self.bus.publish(ev)
        await self.notify(ev)

    def create_item(
        self, quantity: Optional[float] = None, initialize=None, register=True, **kwargs
    ) -> Entity:
        initialize = initialize if initialize else {}
        if quantity:
            initialize = {carryable.Carryable: dict(quantity=quantity)}
        created = scopes.item(initialize=initialize, **kwargs)
        if register:
            return self.register(created)
        return created

    async def find_item(
        self, candidates=None, scopes=[], exclude=None, number=None, **kwargs
    ) -> Optional[Entity]:
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

        found: Optional[Entity] = None

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