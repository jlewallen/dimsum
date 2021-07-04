from typing import Optional, List, Sequence, Dict, Union, Any, Literal, Callable, cast

import logging
import dataclasses
import time

import model.game as game
import model.reply as reply
import model.entity as entity
import model.world as world

import model.scopes.movement as movement
import model.scopes.carryable as carryable
import model.scopes.occupyable as occupyable
import model.scopes.behavior as behavior
import model.scopes as scopes

from bus import EventBus

import context
import luaproxy
import serializing
import proxying
import storage

log = logging.getLogger("dimsum.model")
scripting = behavior.ScriptEngine()
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
        context_factory: Optional[Callable] = None,
        handlers: Optional[List[Any]] = None,
    ):
        super().__init__()
        assert store
        assert context_factory
        self.store: storage.EntityStorage = store
        self.context_factory: Callable = context_factory
        self.world: Optional[world.World] = None
        self.bus = EventBus(handlers=handlers or [])
        self.registrar = entity.Registrar()

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

    async def perform(
        self, action, person: Optional[entity.Entity] = None, **kwargs
    ) -> game.Reply:

        log.info("-" * 100)
        log.info("%s", action)
        log.info("-" * 100)

        await self.prepare()

        assert self.world

        area = self.world.find_entity_area(person) if person else None

        with WorldCtx(
            person=person,
            area=area,
            session=self,
            context_factory=self.context_factory,
            **kwargs
        ) as ctx:
            try:
                return await action.perform(
                    world=self.world, area=area, person=person, ctx=ctx
                )
            except entity.EntityFrozen:
                return reply.Failure("whoa, that's frozen")

    async def tick(self, now: Optional[float] = None):
        await self.prepare()

        if now is None:
            now = time.time()

        await self.everywhere(world.TickHook, time=now)
        await self.everywhere(world.WindHook, time=now)

        return now

    async def everywhere(self, name: str, **kwargs):
        assert self.world

        log.info("everywhere:%s %s", name, kwargs)
        everything: List[entity.Entity] = []
        with self.world.make(behavior.BehaviorCollection) as world_behaviors:
            everything = world_behaviors.entities
        for entity in everything:
            with entity.make(behavior.Behaviors) as behave:
                behaviors = behave.get_behaviors(name)
                if len(behaviors) > 0:
                    log.info("everywhere: %s", entity)
                    area = self.world.find_entity_area(entity)
                    assert area
                    with WorldCtx(
                        area=area,
                        entity=entity,
                        session=self,
                        context_factory=self.context_factory,
                        **kwargs
                    ) as ctx:
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
        self.context_factory = luaproxy.context_factory
        self.handlers = handlers or []

    def session(self, handlers=None) -> "Session":
        log.info("session:new")
        combined = (handlers or []) + self.handlers
        return Session(
            store=self.store, context_factory=self.context_factory, handlers=combined
        )

    async def reload(self):
        return Domain(empty=True, store=self.store)


class WorldCtx(context.Ctx):
    def __init__(
        self,
        session: Optional[Session] = None,
        person: Optional[entity.Entity] = None,
        context_factory=None,
        **kwargs
    ):
        super().__init__()
        assert session
        assert world
        self.person = person
        self.se = scripting
        self.session = session
        self.world = session.world
        self.registrar = session.registrar
        self.bus = session.bus
        self.context_factory = context_factory
        self.scope = behavior.Scope(world=world, person=person, **kwargs)
        assert isinstance(self.world, world.World)

    def __enter__(self):
        context.set(self)
        return self

    def __exit__(self, type, value, traceback):
        context.set(None)
        return False

    def extend(self, **kwargs) -> "WorldCtx":
        self.scope = self.scope.extend(**kwargs)
        return self

    def entities(self) -> List[entity.Entity]:
        def get_entities_inside(array):
            return flatten([get_entities(e) for e in array])

        def get_entities(thing):
            if isinstance(thing, entity.Entity):
                return [thing]
            if isinstance(thing, list):
                return get_entities_inside(thing)
            return []

        return get_entities_inside(self.scope.values())

    def register(self, entity: entity.Entity) -> entity.Entity:
        return self.session.register(entity)

    def unregister(self, destroyed: entity.Entity) -> entity.Entity:
        entity.cleanup(destroyed, world=self.world)
        return self.session.unregister(destroyed)

    async def publish(self, *args, **kwargs):
        for arg in args:
            await self.bus.publish(arg)

    async def hook(self, name: str) -> None:
        found = {}
        entities = self.entities()
        log.info("hook:%s %s" % (name, entities))
        for entity in entities:
            behaviors = entity.make(behavior.Behaviors).get_behaviors(name)
            if len(behaviors) > 0:
                log.info(
                    "hook:%s invoke '%s' %d behavior" % (name, entity, len(behaviors))
                )
            found[entity] = behaviors

        scope = self.scope
        for entity, behaviors in found.items():

            def create_context():
                return self.context_factory(creator=entity)

            for b in behaviors:
                prepared = self.se.prepare(scope, create_context)
                thunk = behavior.GenericThunk
                if "person" in scope.map and scope.map["person"]:
                    thunk = behavior.PersonThunk
                actions = self.se.execute(thunk, prepared, b)
                if actions:
                    for action in actions:
                        await self.session.perform(action, person=self.person)
                        log.info("performing: %s", action)
                entity.touch()

    def create_item(
        self, quantity: Optional[float] = None, initialize=None, **kwargs
    ) -> entity.Entity:
        initialize = initialize if initialize else {}
        if quantity:
            initialize = {carryable.Carryable: dict(quantity=quantity)}
        return scopes.item(initialize=initialize, **kwargs)

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
