from typing import Any, Optional, Dict, List, Sequence, cast

import time
import logging
import entity
import context
import props
import game
import bus
import behavior
import things
import envo
import living
import animals

DefaultMoveVerb = "walk"
log = logging.getLogger("dimsum")
scripting = behavior.ScriptEngine()


class World(entity.Entity, entity.Registrar):
    def __init__(self, bus: bus.EventBus, context_factory):
        super().__init__()
        self.details = props.Details("World", desc="Ya know, everything")
        self.key = "world"
        self.bus = bus
        self.context_factory = context_factory

    def items(self):
        return self.all_of_type(things.Item)

    def areas(self):
        return self.all_of_type(envo.Area)

    def people(self):
        return self.all_of_type(animals.Person)

    def players(self):
        return self.all_of_type(animals.Player)

    def find_person_by_name(self, name):
        for person in self.people():
            if person.details.name == name:
                return person
        return None

    def welcome_area(self):
        return self.areas()[0]

    def find_entity_area(self, entity: entity.Entity):
        for area in self.areas():
            if area.contains(entity) or area.occupying(entity):
                return area
        return None

    def find_player_area(self, player: animals.Person):
        return self.find_entity_area(player)

    def contains(self, key):
        return key in self.entities

    def find(self, key):
        return self.entities[key]

    def resolve(self, keys):
        return [self.entities[key] for key in keys]

    def add_area(self, area: envo.Area):
        self.register(area)
        for entity in area.entities():
            self.register(entity)
        for item in area.items:
            for linked in item.adjacent():
                log.info("linked: %s", linked)
                self.add_area(cast(envo.Area, linked))

    def build_new_area(
        self,
        person: animals.Person,
        entry: things.Item,
        verb: str = DefaultMoveVerb,
    ):
        log.info("building new area")

        fromArea: envo.Area = self.find_player_area(person)
        theWayBack = things.Item(creator=person, details=entry.details.clone())
        theWayBack.link_area(fromArea, verb=verb)

        area = envo.Area(
            creator=person,
            details=props.Details(
                "A pristine, new place.",
                desc="Nothing seems to be here, maybe you should decorate?",
            ),
        )
        area.add_item(theWayBack)
        self.add_area(area)
        return area

    def search_hands(self, person: animals.Person, whereQ: str):
        return person.find(whereQ)

    def search_floor(self, person: animals.Person, whereQ: str):
        area = self.find_player_area(person)
        return area.find(whereQ)

    def search(self, person: animals.Person, whereQ: str, unheld=None, **kwargs):
        area = self.find_player_area(person)

        order = [person.find, area.find]

        if unheld:
            order = [area.find, person.find]

        for fn in order:
            item = fn(whereQ)
            if item:
                return item

        return None

    async def perform(self, action, person: Optional[animals.Person]):
        area = self.find_player_area(person) if person else None
        ctx = WorldCtx(self.context_factory, world=self, person=person, area=area)
        return await action.perform(ctx, self, person)

    async def tick(self, now: Optional[float] = None):
        if now is None:
            now = time.time()
        return await self.everywhere("tick", time=now)

    async def everywhere(self, name: str, **kwargs):
        log.info("everywhere:%s %s", name, kwargs)
        everything = list(self.entities.values())
        for entity in everything:
            behaviors = entity.get_behaviors(name)
            if len(behaviors) > 0:
                log.info("tick: %s", entity)
                area = self.find_entity_area(entity)
                ctx = WorldCtx(
                    self.context_factory, world=self, area=area, entity=entity, **kwargs
                )
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


def flatten(l):
    return [item for sl in l for item in sl]
