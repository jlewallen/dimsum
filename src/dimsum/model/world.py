from typing import Any, Optional, Dict, List, Sequence, cast
import time
import logging
import inflect

import bus
import context

import model.entity as entity
import model.properties as properties
import model.game as game
import model.behavior as behavior
import model.occupyable as occupyable
import model.carryable as carryable
import model.movement as movement
import model.scopes as scopes

DefaultMoveVerb = "walk"
TickHook = "tick"
WindHook = "wind"
log = logging.getLogger("dimsum")
scripting = behavior.ScriptEngine()
p = inflect.engine()


class EntityHooks(entity.Hooks):
    def describe(self, entity: entity.Entity) -> str:
        with entity.make_and_discard(carryable.Carryable) as carry:
            if carry.quantity > 1:
                return "{0} {1} (#{2})".format(
                    carry.quantity,
                    p.plural(entity.props.name, carry.quantity),
                    entity.props.gid,
                )
        return "{0} (#{1})".format(p.a(entity.props.name), entity.props.gid)


entity.hooks(EntityHooks())


class World(entity.Entity, entity.Registrar):
    def __init__(self, bus: bus.EventBus, context_factory, **kwargs):
        super().__init__(
            key="world",
            props=properties.Common("World", desc="Ya know, everything"),
            scopes=scopes.World,
            **kwargs
        )
        self.bus = bus
        self.context_factory = context_factory
        self.register(self)

    def find_entity_by_name(self, name):
        for key, e in self.entities.items():
            if name in e.props.name:
                return e
        return None

    def find_person_by_name(self, name) -> Optional[entity.Entity]:
        for key, e in self.entities.items():
            # TODO Check type
            if e.props.name == name:
                return e
        return None

    def welcome_area(self) -> entity.Entity:
        for _, entity in self.entities.items():
            if entity.has(occupyable.Occupyable):
                return entity
        raise Exception("no welcome area")

    def find_entity_area(self, entity: entity.Entity) -> Optional[entity.Entity]:
        log.info("finding area for %s", entity)
        if entity.has(occupyable.Occupyable):
            return entity
        for _, needle in self.entities.items():
            with needle.make(carryable.Containing) as contain:
                if contain.contains(entity) or needle.make(
                    occupyable.Occupyable
                ).occupying(entity):
                    return needle
        return None

    def find_player_area(self, player: entity.Entity) -> entity.Entity:
        area = self.find_entity_area(player)
        assert area
        return area

    def contains(self, key) -> bool:
        return key in self.entities

    def find_by_key(self, key) -> entity.Entity:
        return self.entities[key]

    def resolve(self, keys) -> Sequence[entity.Entity]:
        return [self.entities[key] for key in keys]

    def add_area(self, area: entity.Entity, depth=0, seen: Dict[str, str] = None):
        if seen is None:
            seen = {}

        if area.key in seen:
            return

        seen[area.key] = area.key

        log.debug("add-area:%d %s %s", depth, area.key, area)

        self.register(area)

        for entity in area.make(occupyable.Occupyable).occupied:
            self.register(entity)

        for entity in area.make(carryable.Containing).holding:
            self.register(entity)

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

    def add_entities(self, entities: List[entity.Entity]):
        for entity in entities:
            log.debug("add-entity: %s %s", entity.key, entity)
            self.register(entity)

    def apply_item_finder(
        self, person: entity.Entity, finder, **kwargs
    ) -> Optional[entity.Entity]:
        assert person
        assert finder
        area = self.find_player_area(person)
        log.info("applying finder:%s %s", finder, kwargs)
        found = finder.find_item(area=area, person=person, world=self, **kwargs)
        if found:
            log.info("found: {0}".format(found))
        else:
            log.info("found: nada")
        return found

    async def perform(self, action, person: Optional[entity.Entity]) -> game.Reply:
        area = self.find_entity_area(person) if person else None
        with WorldCtx(
            self.context_factory, world=self, person=person, area=area
        ) as ctx:
            try:
                return await action.perform(ctx, self, person)
            except entity.EntityFrozen:
                return game.Failure("whoa, that's frozen")

    async def tick(self, now: Optional[float] = None):
        if now is None:
            now = time.time()
        await self.everywhere(TickHook, time=now)
        await self.everywhere(WindHook, time=now)
        return now

    async def everywhere(self, name: str, **kwargs):
        log.info("everywhere:%s %s", name, kwargs)
        everything = list(self.entities.values())
        for entity in everything:
            with entity.make(behavior.Behaviors) as behave:
                behaviors = behave.get_behaviors(name)
                if len(behaviors) > 0:
                    log.info("everywhere: %s", entity)
                    area = self.find_entity_area(entity)
                    assert area
                    if (
                        area == entity
                    ):  # HACK I think the default here should actually be entity.
                        entity = None
                    with WorldCtx(
                        self.context_factory,
                        world=self,
                        area=area,
                        entity=entity,
                        **kwargs
                    ) as ctx:
                        await ctx.hook(name)

    def __str__(self):
        return "$world"

    def __repr__(self):
        return "$world"


class WorldCtx(context.Ctx):
    # This should eventually get worked out. Just return Ctx from this function?
    def __init__(
        self,
        context_factory,
        world: World = None,
        person: entity.Entity = None,
        **kwargs
    ):
        super().__init__()
        assert world
        self.se = scripting
        self.context_factory = context_factory
        self.world = world
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

    def registrar(self) -> entity.Registrar:
        return self.world

    async def publish(self, *args, **kwargs):
        for arg in args:
            await self.world.bus.publish(arg)

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
                        await self.world.perform(action, self.person)
                        log.info("performing: %s", action)

    def create_item(
        self, quantity: float = None, initialize=None, **kwargs
    ) -> entity.Entity:
        initialize = initialize if initialize else {}
        if quantity:
            initialize = {carryable.Carryable: dict(quantity=quantity)}
        return scopes.item(initialize=initialize, **kwargs)

    def find_item(
        self, candidates=None, scopes=[], exclude=None, **kwargs
    ) -> Optional[entity.Entity]:
        log.info(
            "find-item: candidates=%s exclude=%s scopes=%s kw=%s",
            candidates,
            exclude,
            scopes,
            kwargs,
        )

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
