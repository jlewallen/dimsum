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
        self.registrar = domain.registrar
        self.world = domain.world

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        return False

    async def materialize(
        self, key: str = None, json: str = None
    ) -> Optional[entity.Entity]:
        return await serializing.materialize(
            registrar=self.registrar, store=self.domain.store, key=key, json=json
        )

    async def perform(
        self, action, person: Optional[entity.Entity], **kwargs
    ) -> game.Reply:
        assert self.world
        area = self.world.find_entity_area(person) if person else None
        with WorldCtx(
            self.domain.context_factory,
            session=self,
            world=self.world,
            person=person,
            area=area,
            registrar=self.registrar,
            **kwargs
        ) as ctx:
            try:
                return await action.perform(ctx, self.world, person)
            except entity.EntityFrozen:
                return game.Failure("whoa, that's frozen")

    async def tick(self, now: Optional[float] = None):
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
                        self.domain.context_factory,
                        session=self,
                        world=self.world,
                        area=area,
                        entity=entity,
                        registrar=self.registrar,
                        **kwargs
                    ) as ctx:
                        await ctx.hook(name)

    def add_area(self, area: entity.Entity, depth=0, seen: Dict[str, str] = None):
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
                    welcoming.area = area
            else:
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
                self.add_area(maybe_area, depth=depth + 1, seen=seen)

            for linked in item.make(movement.Movement).adjacent():
                log.debug("linked-via-item[%d]: %s (%s)", depth, linked, item)
                self.add_area(linked, depth=depth + 1, seen=seen)

        for linked in area.make(movement.Movement).adjacent():
            log.debug("linked-adj[%d]: %s", depth, linked)
            self.add_area(linked, depth=depth + 1, seen=seen)

        log.debug("area-done:%d %s", depth, area.key)


class Domain:
    def __init__(self, bus: bus.EventBus = None, store=None, empty=False, **kwargs):
        super().__init__()
        self.bus = (
            bus if bus else messages.TextBus(handlers=[handlers.WhateverHandlers])
        )
        self.store = store if store else storage.InMemory()
        self.context_factory = luaproxy.context_factory
        self.registrar = entity.Registrar()
        self.world = None
        if not empty:
            self.world = world.World()
            self.registrar.register(self.world)

    def session(self) -> Session:
        return Session(self)

    async def reload(self):
        await self.store.update(serializing.registrar(self.registrar))

        reloaded = Domain(empty=True, store=self.store)
        reloaded.world = await reloaded.materialize(key=world.Key)
        return reloaded

    async def materialize(
        self, key: str = None, json: str = None
    ) -> Optional[entity.Entity]:
        return await serializing.materialize(
            registrar=self.registrar, store=self.store, key=key, json=json
        )

    async def purge(self):
        self.registrar.purge()

    async def load(self, create=False):
        self.registrar.purge()
        log.info("loading %s", self.store)
        self.world = await self.materialize(key=world.Key)
        if self.world:
            return
        if create:
            self.world = world.World()
            self.registrar.register(self.world)

    async def save(self):
        log.info("saving %s", self.store)
        await self.store.update(serializing.registrar(self.registrar))


class WorldCtx(context.Ctx):
    # This should eventually get worked out. Just return Ctx from this function?
    def __init__(
        self,
        context_factory,
        session: Session = None,
        registrar: entity.Registrar = None,
        world: world.World = None,
        person: entity.Entity = None,
        **kwargs
    ):
        super().__init__()
        assert session
        assert world
        assert registrar
        self.se = scripting
        self.session = session
        self.domain = session.domain
        self.bus = self.domain.bus
        self.world = world
        self.context_factory = context_factory
        self.registrar = registrar
        self.person = person
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
        return self.registrar.register(entity)

    def unregister(self, entity: entity.Entity) -> entity.Entity:
        return self.registrar.unregister(entity)

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

    def find_item(
        self, candidates=None, scopes=[], exclude=None, number=None, **kwargs
    ) -> Optional[entity.Entity]:
        log.info(
            "find-item: number=%s candidates=%s exclude=%s scopes=%s kw=%s",
            number,
            candidates,
            exclude,
            scopes,
            kwargs,
        )

        if number:
            return self.registrar.find_by_number(number)

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
