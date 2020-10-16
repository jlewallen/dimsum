from typing import List, Tuple, Dict

import logging
import sys
import time
import inflect
import uuid

import props
import entity
import behavior

p = inflect.engine()

MemoryAreaKey = "m:area"


class Event:
    pass


class EventBus:
    async def publish(self, event: Event):
        logging.info("publish:%s", event)


class Activity:
    pass


class Item(entity.Entity):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.areas = kwargs["areas"] if "areas" in kwargs else {}
        self.validate()

    def touch(self):
        self.details.touch()

    def describes(self, q: str):
        return q.lower() in self.details.name.lower()

    def observe(self):
        return ObservedEntity(self)

    def saved(self):
        p = super().saved()
        p.update(
            {
                "areas": {k: v.key for k, v in self.areas.items()},
            }
        )
        return p

    def load(self, world, properties):
        super().load(world, properties)
        self.areas = {}
        if "areas" in properties:
            self.areas = {
                key: world.find(value) for key, value in properties["areas"].items()
            }

    def accept(self, visitor: entity.EntityVisitor):
        return visitor.item(self)

    def __str__(self):
        return p.a(self.details.name)

    def __repr__(self):
        return str(self)


class MaybeItem:
    def __init__(self, name: str):
        self.name = name

    def make(self, player):
        return Item(details=props.Details(self.name), owner=player)


class Recipe(Item):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.required = kwargs["required"] if "required" in kwargs else {}
        self.base = kwargs["base"] if "base" in kwargs else {}
        self.validate()

    def accept(self, visitor: entity.EntityVisitor):
        return visitor.recipe(self)

    def saved(self):
        p = super().saved()
        p.update(
            {
                "base": self.base,
                "required": {k: e.key for k, e in self.required.items()},
            }
        )
        return p

    def load(self, world, properties):
        super().load(world, properties)
        self.base = properties["base"] if "base" in properties else {}
        self.required = {k: world.find(v) for k, v in properties["required"].items()}

    def invoke(self, player):
        return Item(owner=player, details=props.Details.from_base(self.base))


class ObservedEntity:
    def __init__(self, entity: entity.Entity):
        self.entity = entity

    def accept(self, visitor):
        return visitor.observed_entity(self)

    def __str__(self):
        return str(self.entity)

    def __repr__(self):
        return str(self)


class ObservedEntities:
    def __init__(self, entities: List[entity.Entity]):
        self.entities = entities

    def accept(self, visitor):
        return visitor.observed_entities(self)

    def __str__(self):
        return str(p.join(self.entities))

    def __repr__(self):
        return str(self)


class Holding(Activity):
    def __init__(self, item: Item):
        super().__init__()
        self.item = item

    def __str__(self):
        return "holding %s" % (self.item,)

    def __repr__(self):
        return str(self)


class Person(entity.Entity):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.holding: List[entity.Entity] = []
        self.wearing: List[entity.Entity] = []
        self.memory = {}

    @property
    def holding(self):
        return self.__holding

    @holding.setter
    def holding(self, value):
        self.__holding = value

    @property
    def wearing(self):
        return self.__wearing

    @holding.setter
    def wearing(self, value):
        self.__wearing = value

    @property
    def memory(self):
        return self.__memory

    @memory.setter
    def memory(self, value):
        self.__memory = value

    def find(self, q: str):
        for entity in self.holding:
            if entity.describes(q):
                return entity
        return None

    def observe(self):
        activities = [Holding(e) for e in self.holding if isinstance(e, Item)]
        return ObservedPerson(self, activities)

    def describes(self, q: str):
        return q.lower() in self.details.name.lower()

    def find_memory(self, q: str):
        for name, entity in self.memory.items():
            if entity.describes(q):
                return name, entity
        return None, None

    def find_recipe(self, q: str):
        for name, entity in self.memory.items():
            if name.startswith("r:"):
                name = name.replace("r:", "")
                if q.lower() in name.lower():
                    return entity
        return None

    def is_wearing(self, item):
        return item in self.wearing

    def wear(self, item: Item):
        if not self.is_holding(item):
            raise Exception("wear before hold")
        self.drop(item)
        if self.is_holding(item):
            raise Exception("wear before hold")
        self.wearing.append(item)
        item.touch()

    def is_holding(self, item):
        return item in self.holding

    def hold(self, item: Item):
        self.holding.append(item)
        item.touch()

    def remove(self, item: Item):
        if not self.is_wearing(item):
            raise Exception("remove before wear")
        self.hold(item)
        self.wearing.remove(item)
        item.touch()

    def consume(self, item):
        FoodFields = [
            props.SumFields("sugar"),
            props.SumFields("fat"),
            props.SumFields("protein"),
            props.SumFields("toxicity"),
            props.SumFields("caffeine"),
            props.SumFields("alcohol"),
            props.SumFields("nutrition"),
            props.SumFields("vitamins"),
        ]
        changes = props.merge_dictionaries(
            self.details.map, item.details.map, FoodFields
        )
        logging.info("merged %s" % (changes,))
        self.details.update(changes)

    def drop_all(self):
        dropped = []
        while len(self.holding) > 0:
            item = self.holding[0]
            self.drop(item)
            item.touch()
            dropped.append(item)
        return dropped

    def drop(self, item: Item):
        if item in self.holding:
            self.holding.remove(item)
            item.touch()
            return [item]
        return []

    def accept(self, visitor: entity.EntityVisitor):
        return visitor.person(self)

    def __str__(self):
        return self.details.name

    def __repr__(self):
        return str(self)

    def saved(self):
        p = super().saved()
        p.update(
            {
                "holding": [e.key for e in self.holding],
                "wearing": [e.key for e in self.wearing],
                "memory": {k: e.key for k, e in self.memory.items()},
            }
        )
        return p

    def load(self, world, properties):
        super().load(world, properties)
        self.holding = (
            world.resolve(properties["holding"]) if "holding" in properties else []
        )
        self.wearing = (
            world.resolve(properties["wearing"]) if "wearing" in properties else []
        )
        self.memory = {}
        if "memory" in properties:
            self.memory = {k: world.find(v) for k, v in properties["memory"].items()}


class ObservedPerson:
    def __init__(self, person: Person, activities: List[Activity]):
        self.person = person
        self.activities = activities

    @property
    def holding(self):
        return self.person.holding

    @property
    def memory(self):
        return self.person.memory

    def accept(self, visitor):
        return visitor.observed_person(self)

    def __str__(self):
        if len(self.activities) == 0:
            return "%s" % (self.person,)
        return "%s who is %s" % (self.person, p.join(list(map(str, self.activities))))

    def __repr__(self):
        return str(self)


class Player(Person):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class Reply:
    def accept(self, visitor):
        raise Error("unimplemented")


class SimpleReply(Reply):
    def __init__(self, message: str):
        self.message = message


class Success(SimpleReply):
    def accept(self, visitor):
        return visitor.success(self)

    def __str__(self):
        return "Success<%s>" % (self.message,)


class Failure(SimpleReply):
    def accept(self, visitor):
        return visitor.failure(self)

    def __str__(self):
        return "Success<%s>" % (self.message,)


class Observation(Reply):
    pass


class PersonalObservation(Observation):
    def __init__(self, who: ObservedPerson):
        self.who = who

    @property
    def details(self):
        return self.who.person.details

    @property
    def properties(self):
        return self.details.map

    @property
    def memory(self):
        return self.who.memory

    def accept(self, visitor):
        return visitor.personal_observation(self)

    def __str__(self):
        return "%s considers themselves %s" % (
            self.who,
            self.properties,
        )


class DetailedObservation(Observation):
    def __init__(self, who: ObservedPerson, what: entity.Entity):
        self.who = who
        self.what = what

    @property
    def details(self):
        return self.what.details

    @property
    def properties(self):
        return self.details.map

    def accept(self, visitor):
        return visitor.detailed_observation(self)

    def __str__(self):
        return "%s observes %s" % (
            self.who,
            self.properties,
        )


class EntitiesObservation(Observation):
    def __init__(self, entities: List[entity.Entity]):
        self.entities = entities

    def accept(self, visitor):
        return visitor.entities_observation(self)


class AreaObservation(Observation):
    def __init__(
        self,
        who: ObservedPerson,
        where: entity.Entity,
        people: List[ObservedPerson],
        items: List[ObservedEntity],
    ):
        self.who = who
        self.where = where
        self.people = people
        self.items = items

    @property
    def details(self):
        return self.where.details

    def accept(self, visitor):
        return visitor.area_observation(self)

    def __str__(self):
        return "%s observes %s, also here %s and visible is %s" % (
            self.who,
            self.details,
            self.people,
            self.items,
        )


class Area(entity.Entity):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.owner = kwargs["owner"]
        self.details = kwargs["details"]
        self.here: List[entity.Entity] = []

    def entities(self):
        return self.here

    def contains(self, e: entity.Entity):
        return e in self.here

    def remove(self, e: entity.Entity):
        self.here.remove(e)
        return self

    def look(self, player: Player):
        people = [
            e.observe() for e in self.here if isinstance(e, Person) and e != player
        ]
        items = [e.observe() for e in self.here if isinstance(e, Item)]
        return AreaObservation(player.observe(), self, people, items)

    def add_item(self, item: Item):
        self.here.append(item)
        return self

    def find(self, q: str):
        for entity in self.here:
            if entity.describes(q):
                return entity
        return None

    def saved(self):
        p = super().saved()
        p.update(
            {
                "details": self.details.map,
                "owner": self.owner.key,
                "here": [e.key for e in self.entities()],
            }
        )
        return p

    def load(self, world, properties):
        super().load(world, properties)
        self.details = props.Details.from_map(properties["details"])
        self.here = world.resolve(properties["here"])

    def accept(self, visitor: entity.EntityVisitor):
        return visitor.area(self)

    def __str__(self):
        return self.details.name

    def __repr__(self):
        return str(self)

    async def entered(self, bus: EventBus, player: Player):
        self.here.append(player)
        await bus.publish(PlayerEnteredArea(player, self))

    async def left(self, bus: EventBus, player: Player):
        self.here.remove(player)
        await bus.publish(PlayerLeftArea(player, self))

    async def drop(self, bus: EventBus, player: Player):
        dropped = player.drop_all()
        for item in dropped:
            self.here.append(item)
            await bus.publish(ItemDropped(player, self, item))
        return dropped

class LupaWorld:
    def __init__(self, entity):
        self.entity = entity

    def __setitem__(self, key, value):
        print("worldworld s", self, key, value)

    def __getitem__(self, key):
        print("worldworld g", self, key)

class LupaArea:
    def __init__(self, entity):
        self.entity = entity

    def __setitem__(self, key, value):
        print("arearea s", self, key, value)

    def __getitem__(self, key):
        print("arearea g", self, key)

class LupaItem:
    def __init__(self, entity):
        self.entity = entity

    def __setitem__(self, key, value):
        print("itemitem s", self, key, value)

    def __getitem__(self, key):
        print("itemitem g", self, key)

class LupaPerson:
    def __init__(self, entity):
        self.entity = entity

    def __setitem__(self, key, value):
        print("personperson s", self, key, value)

    def __getitem__(self, key):
        print("personperson g", self, key)

def lupa_for(entity: entity.Entity):
    if entity is None:
        return None
    if isinstance(entity, World):
        return LupaWorld(entity)
    if isinstance(entity, Person):
        return LupaPerson(entity)
    if isinstance(entity, Area):
        return LupaArea(entity)
    if isinstance(entity, Item):
        return LupaItem(entity)
    raise Exception("no wrapper for entity: %s" % (entity,))

class World(entity.Entity):
    def __init__(self, bus: EventBus):
        super().__init__()
        self.details = props.Details("World", desc="Ya know, everything")
        self.key = "world"
        self.bus = bus
        self.entities: Dict[str, entity.Entity] = {}

    def register(self, entity: entity.Entity):
        self.entities[entity.key] = entity

    def unregister(self, entity: entity.Entity):
        del self.entities[entity.key]

    def empty(self):
        return len(self.entities.keys()) == 0

    def areas(self):
        return [e for e in self.entities.values() if isinstance(e, Area)]

    def people(self):
        return [e for e in self.entities.values() if isinstance(e, Person)]

    def players(self):
        return [e for e in self.entities.values() if isinstance(e, Player)]

    def find_person_by_name(self, name):
        for person in self.people():
            if person.details.name == name:
                return person
        return None

    def welcome_area(self):
        return self.areas()[0]

    def look(self, player: Player):
        area = self.find_player_area(player)
        return area.look(player)

    def find_entity_area(self, entity: entity.Entity):
        for area in self.areas():
            if area.contains(entity):
                return area
        return None

    def find_player_area(self, player: Player):
        return self.find_entity_area(player)

    def contains(self, key):
        return key in self.entities

    def find(self, key):
        return self.entities[key]

    def resolve(self, keys):
        return [self.entities[key] for key in keys]

    def add_area(self, area: Area):
        self.register(area)
        for entity in area.entities():
            self.register(entity)

    def build_new_area(self, player: Player, fromArea: Area, entry: Item):
        theWayBack = Item(owner=player, details=entry.details.clone(), area=fromArea)
        area = Area(
            owner=player,
            details=props.Details(
                "A pristine, new place.",
                desc="Nothing seems to be here, maybe you should decorate?",
            ),
        )
        area.add_item(theWayBack)
        self.add_area(area)
        return area

    def search_hands(self, player: Player, whereQ: str):
        return player.find(whereQ)

    def search_floor(self, player: Player, whereQ: str):
        area = self.find_player_area(player)
        return area.find(whereQ)

    def search(self, player: Player, whereQ: str, **kwargs):
        area = self.find_player_area(player)

        item = player.find(whereQ)
        if item:
            return area, item

        item = area.find(whereQ)
        if item:
            return area, item

        return None, None

    async def perform(self, player: Player, action):
        area = self.find_player_area(player)
        ctx = Ctx(world=lupa_for(self), person=lupa_for(player), area=lupa_for(area))
        return await action.perform(ctx, self, player)

    def __str__(self):
        return "$world"

    def __repr__(self):
        return "$world"


class HooksAround:
    def __enter__(self):
        return None

    def __exit__(self, type, value, traceback):
        pass


class Ctx:
    def __init__(self, **kwargs):
        self.se = behavior.ScriptEngine()
        self.scope = behavior.Scope(**kwargs)

    def extend(self, **kwargs):
        logging.info("EXTEND-NO-WRAPPERS", kwargs)
        self.scope = self.scope.extend(**kwargs)
        return self

    def entities(self):
        def flatten(l):
            return [item for sl in l for item in sl]

        def get_entities_inside(array):
            return flatten([get_entities(e) for e in array])

        def get_entities(thing):
            if isinstance(thing, entity.Entity):
                return [thing]
            if isinstance(thing, list):
                return get_entities_inside(thing)
            return []

        return get_entities_inside(self.scope.values())

    async def hook(self, name, **kwargs):
        found = []
        entities = self.entities()
        logging.info("hook:%s %s" % (name, entities))
        for entity in entities:
            behaviors = entity.get_behaviors(name)
            if len(behaviors) > 0:
                logging.info(
                    "entity:behaviors invoke '%s' %d behavior"
                    % (entity, len(behaviors))
                )
            found.extend(behaviors)

        scope = self.scope.extend(**kwargs)

        for b in found:
            self.se.execute(behavior.GenericThunk, scope, b)


class Action:
    def __init__(self, **kwargs):
        pass

    async def perform(self, ctx: Ctx, world: World, player: Player):
        raise Exception("unimplemented")


class PlayerJoined(Event):
    def __init__(self, player: Player):
        self.player = player

    def __str__(self):
        return "%s joined" % (self.player)


class PlayerQuit(Event):
    def __init__(self, player: Player):
        self.player = player

    def __str__(self):
        return "%s quit" % (self.player)


class AreaConstructed(Event):
    def __init__(self, player: Player, area: Area):
        self.player = player
        self.area = area

    def __str__(self):
        return "%s constructed %s" % (self.player, self.area)


class PlayerEnteredArea(Event):
    def __init__(self, player: Player, area: Area):
        self.player = player
        self.area = area

    def __str__(self):
        return "%s entered %s" % (self.player, self.area)


class PlayerLeftArea(Event):
    def __init__(self, player: Player, area: Area):
        self.player = player
        self.area = area

    def __str__(self):
        return "%s left %s" % (self.player, self.area)


class ItemHeld(Event):
    def __init__(self, player: Player, area: Area, item: Item):
        self.player = player
        self.area = area
        self.item = item

    def __str__(self):
        return "%s picked up %s" % (self.player, self.item)


class ItemMade(Event):
    def __init__(self, player: Player, area: Area, item: Item):
        self.player = player
        self.area = area
        self.item = item

    def __str__(self):
        return "%s created %s out of thin air!" % (self.player, self.item)


class ItemEaten(Event):
    def __init__(self, player: Player, area: Area, item: Item):
        self.player = player
        self.area = area
        self.item = item

    def __str__(self):
        return "%s just ate %s!" % (self.player, self.item)


class ItemDrank(Event):
    def __init__(self, player: Player, area: Area, item: Item):
        self.player = player
        self.area = area
        self.item = item

    def __str__(self):
        return "%s just drank %s!" % (self.player, self.item)


class ItemDropped(Event):
    def __init__(self, player: Player, area: Area, item: Item):
        self.player = player
        self.area = area
        self.item = item

    def __str__(self):
        return "%s dropped %s" % (self.player, self.item)


class ItemObliterated(Event):
    def __init__(self, player: Player, area: Area, item: Item):
        self.player = player
        self.area = area
        self.item = item

    def __str__(self):
        return "%s obliterated %s" % (self.player, self.item)
