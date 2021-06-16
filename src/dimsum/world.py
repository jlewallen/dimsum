from typing import Any, Optional, Dict, List, Sequence, cast
import time
import logging
import entity
import context
import properties
import game
import bus
import behavior
import things
import envo
import living
import animals

DefaultMoveVerb = "walk"
TickHook = "tick"
WindHook = "wind"
log = logging.getLogger("dimsum")
scripting = behavior.ScriptEngine()


class World(entity.Entity, entity.Registrar):
    def __init__(self, bus: bus.EventBus, context_factory, **kwargs):
        super().__init__(
            key="world",
            props=properties.Common("World", desc="Ya know, everything"),
            **kwargs
        )
        self.bus = bus
        self.context_factory = context_factory
        self.register(self)

    def items(self):
        return self.all_of_type(things.Item)

    def areas(self):
        return self.all_of_type(envo.Area)

    def people(self):
        return self.all_of_type(animals.Person)

    def players(self):
        return self.all_of_type(animals.Player)

    def find_entity_by_name(self, name):
        for key, e in self.entities.items():
            if name in e.props.name:
                return e
        return None

    def find_person_by_name(self, name) -> Optional[animals.Person]:
        for person in self.people():
            if person.props.name == name:
                return person
        return None

    def welcome_area(self) -> envo.Area:
        return self.areas()[0]

    def find_entity_area(self, entity: entity.Entity) -> Optional[envo.Area]:
        if isinstance(entity, envo.Area):  # HACK
            return entity
        for area in self.areas():
            if area.contains(entity) or area.occupying(entity):
                return area
        return None

    def find_player_area(self, player: animals.Person) -> envo.Area:
        area = self.find_entity_area(player)
        assert area
        return area

    def contains(self, key) -> bool:
        return key in self.entities

    def find_by_key(self, key) -> entity.Entity:
        return self.entities[key]

    def resolve(self, keys) -> Sequence[entity.Entity]:
        return [self.entities[key] for key in keys]

    def add_area(self, area: envo.Area, depth=0, seen: Dict[str, str] = None):
        if seen is None:
            seen = {}

        if area.key in seen:
            return

        seen[area.key] = area.key

        log.debug("add-area:%d %s %s", depth, area.key, area)

        self.register(area)

        for entity in area.entities():
            self.register(entity)

        for item in area.entities():
            if item.props.navigable:
                log.debug("linked-via-navigable[%s] %s", depth, item.props.navigable)
                self.add_area(item.props.navigable, depth=depth + 1, seen=seen)

            if isinstance(item, things.Item):
                for linked in item.adjacent():
                    log.debug("linked-via-item[%d]: %s (%s)", depth, linked, item)
                    self.add_area(cast(envo.Area, linked), depth=depth + 1, seen=seen)

        for linked in area.adjacent():
            log.debug("linked-adj[%d]: %s", depth, linked)
            self.add_area(cast(envo.Area, linked), depth=depth + 1, seen=seen)

        log.debug("area-done:%d %s", depth, area.key)

    def add_entities(self, entities: List[entity.Entity]):
        for entity in entities:
            log.debug("add-entity: %s %s", entity.key, entity)
            self.register(entity)

    def apply_item_finder(
        self, person: animals.Person, finder: things.ItemFinder, **kwargs
    ) -> Optional[things.Item]:
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

    async def perform(self, action, person: Optional[animals.Person]) -> game.Reply:
        area = self.find_entity_area(person) if person else None
        with WorldCtx(
            self.context_factory, world=self, person=person, area=area
        ) as ctx:
            try:
                return await action.perform(ctx, self, person)
            except entity.ItemFrozen:
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
            behaviors = entity.get_behaviors(name)
            if len(behaviors) > 0:
                log.info("everywhere: %s", entity)
                area = self.find_entity_area(entity)
                assert area
                if (
                    area == entity
                ):  # HACK I think the default here should actually be entity.
                    entity = None
                with WorldCtx(
                    self.context_factory, world=self, area=area, entity=entity, **kwargs
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
        person: animals.Person = None,
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
            behaviors = entity.get_behaviors(name)
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

    def create_item(self, **kwargs) -> things.Item:
        return things.Item(**kwargs)

    def find_item(
        self, inherits=None, candidates=None, exclude=None, things_only=True, **kwargs
    ) -> Optional[entity.Entity]:
        log.info(
            "find-item: candidates=%s exclude=%s kw=%s", candidates, exclude, kwargs
        )

        if len(candidates) == 0:
            return None

        found: Optional[entity.Entity] = None

        if things_only:
            inherits = things.Item

        for e in candidates:
            if exclude and e in exclude:
                continue

            if inherits and not isinstance(e, inherits):
                continue

            if e.describes(**kwargs):
                return e
            else:
                found = e

        return found


def flatten(l):
    return [item for sl in l for item in sl]
