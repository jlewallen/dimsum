from typing import Optional, List, Sequence, Dict

import logging
import time

import model.game as game
import model.entity as entity
import model.world as world

import model.scopes.movement as movement
import model.scopes.carryable as carryable
import model.scopes.occupyable as occupyable
import model.scopes.behavior as behavior
import model.scopes as scopes

import bus
import context
import luaproxy
import messages
import handlers
import serializing
import storage

log = logging.getLogger("dimsum.model")
scripting = behavior.ScriptEngine()


class Session:
    def __init__(self, domain: "Domain"):
        super().__init__()
        self.domain = domain
        self.registrar = entity.Registrar()
        self.world: Optional[world.World] = None

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        # TODO Warn on unsaved changes?
        return False

    def register(self, entity: entity.Entity) -> entity.Entity:
        return self.registrar.register(entity)

    def unregister(self, entity: entity.Entity) -> entity.Entity:
        return self.registrar.unregister(entity)

    async def materialize(
        self,
        key: str = None,
        gid: int = None,
        json: str = None,
        reach=None,
    ) -> Optional[entity.Entity]:
        return await serializing.materialize(
            registrar=self.registrar,
            store=self.domain.store,
            key=key,
            gid=gid,
            json=json,
            reach=reach,
        )

    async def prepare(self, reach=None):
        if self.world:
            assert self.world in self.registrar.entities.values()
            return self.world

        self.world = await self.materialize(key=world.Key, reach=reach)
        if self.world:
            assert self.world in self.registrar.entities.values()
            return self.world

        log.info("creating new world")
        self.world = world.World()
        self.register(self.world)
        assert self.world in self.registrar.entities.values()
        return self.world

    async def perform(
        self, action, person: Optional[entity.Entity], **kwargs
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
            context_factory=self.domain.context_factory,
            **kwargs
        ) as ctx:
            try:
                return await action.perform(ctx, self.world, person)
            except entity.EntityFrozen:
                return game.Failure("whoa, that's frozen")

        log.info("-" * 100)

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
                        context_factory=self.domain.context_factory,
                        **kwargs
                    ) as ctx:
                        await ctx.hook(name)

    async def add_area(self, area: entity.Entity, depth=0, seen: Dict[str, str] = None):
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

    async def save(self):
        log.info("saving %s", self.domain.store)
        await self.domain.store.update(serializing.registrar(self.registrar))


class Domain:
    def __init__(
        self, bus: bus.EventBus = None, store: storage.EntityStorage = None, **kwargs
    ):
        super().__init__()
        self.bus = (
            bus if bus else messages.TextBus(handlers=[handlers.WhateverHandlers])
        )
        self.store = store if store else storage.InMemory()
        self.context_factory = luaproxy.context_factory

    def session(self) -> "Session":
        log.info("session:new")
        return Session(self)

    async def reload(self):
        reloaded = Domain(empty=True, store=self.store)
        with reloaded.session() as session:
            reloaded.world = await session.materialize(
                key=world.Key
            )  # TODO Move to Session
            return reloaded


class WorldCtx(context.Ctx):
    def __init__(
        self,
        session: Session = None,
        person: entity.Entity = None,
        context_factory=None,
        **kwargs
    ):
        super().__init__()
        assert session
        assert world
        self.person = person
        self.se = scripting
        self.session = session
        self.domain = session.domain
        self.world = session.world
        self.registrar = session.registrar
        self.bus = session.domain.bus
        self.context_factory = context_factory
        self.scope = behavior.Scope(world=world, person=person, **kwargs)

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

    def unregister(self, entity: entity.Entity) -> entity.Entity:
        return self.session.unregister(entity)

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
                        await self.session.perform(action, self.person)
                        log.info("performing: %s", action)

    def create_item(
        self, quantity: float = None, initialize=None, **kwargs
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
            return await self.session.materialize(gid=number)

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
