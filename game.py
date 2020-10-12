from typing import List, Tuple

import asyncio
import logging
import sys
import time
import inflect
import uuid

p = inflect.engine()


class NotYours(Exception):
    pass


class SorryError(Exception):
    pass


class AlreadyHolding(Exception):
    pass


class NotHoldingAnything(Exception):
    pass


class HoldingTooMuch(Exception):
    pass


class UnknownField(Exception):
    pass


class Visitor:
    def item(self, item):
        pass

    def person(self, person):
        pass

    def area(self, area):
        pass


class Entity:
    def __init__(self, **kwargs):
        if "key" in kwargs:
            self.key = kwargs["key"]
        else:
            self.key = str(uuid.uuid1())

    def describes(self, q: str):
        return False

    def saved(self):
        return {
            "key": self.key,
        }

    def load(self, world, properties):
        self.key = properties["key"]

    def accept(self, visitor: Visitor):
        raise Exception("unimplemented")


class Event:
    pass


class EventBus:
    async def publish(self, event: Event):
        logging.info("publish:%s", event)


class Details:
    def __init__(self, name: str = "", desc: str = "", presence: str = ""):
        self.name = name
        self.desc = desc
        self.presence = presence
        self.created = time.time()
        self.touched = time.time()

    def __str__(self):
        return self.name

    def touch(self):
        self.touched = time.time()

    def clone(self):
        return Details(self.name, self.desc, self.presence)


class Activity:
    pass


class Item(Entity):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.owner = kwargs["owner"]
        self.details = kwargs["details"]
        self.area = kwargs["area"] if "area" in kwargs else None

    def touch(self):
        self.details.touch()

    def describes(self, q: str):
        return q.lower() in self.details.name.lower()

    def observe(self):
        return ObservedItem(self)

    def saved(self):
        p = super().saved()
        p.update(
            {
                "details": self.details.__dict__,
                "area": self.area.key if self.area else None,
            }
        )
        return p

    def load(self, world, properties):
        super().load(world, properties)
        self.details.__dict__ = properties["details"]
        self.area = world.find(properties["area"]) if properties["area"] else None

    def accept(self, visitor: Visitor):
        return visitor.item(self)

    def __str__(self):
        return p.a(self.details.name)

    def __repr__(self):
        return str(self)


class ObservedItem:
    def __init__(self, item: Item, where: str = ""):
        self.item = item
        self.where = where

    def __str__(self):
        return str(self.item)

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


class Person(Entity):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.owner = kwargs["owner"]
        self.details = kwargs["details"]
        self.creator = kwargs["creator"] if "creator" in kwargs else True
        self.holding: List[Entity] = []
        self.memory = None

    @property
    def holding(self):
        return self.__holding

    @holding.setter
    def holding(self, value):
        self.__holding = value

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

    def is_holding(self, item):
        return item in self.holding

    def hold(self, item: Item):
        self.holding.append(item)
        item.touch()

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

    def accept(self, visitor: Visitor):
        return visitor.person(self)

    def __str__(self):
        return self.details.name

    def saved(self):
        p = super().saved()
        p.update(
            {
                "details": self.details.__dict__,
                "holding": [e.key for e in self.holding],
                "creator": self.creator,
                "memory": self.memory.key if self.memory else None,
            }
        )
        return p

    def load(self, world, properties):
        super().load(world, properties)
        self.details.__dict__ = properties["details"]
        self.holding = world.resolve(properties["holding"])
        if "memory" in properties and properties["memory"]:
            self.memory = world.find(properties["memory"])


class ObservedPerson:
    def __init__(self, person: Person, activities: List[Activity]):
        self.person = person
        self.activities = activities

    @property
    def holding(self):
        return self.person.holding

    def __str__(self):
        if len(self.activities) == 0:
            return "%s" % (self.person,)
        return "%s who is %s" % (self.person, p.join(self.activities))

    def __repr__(self):
        return str(self)


class Player(Person):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class Observation:
    def __init__(
        self,
        who: ObservedPerson,
        details: Details,
        people: List[ObservedPerson],
        items: List[ObservedItem],
    ):
        self.who = who
        self.details = details
        self.people = people
        self.items = items

    def __str__(self):
        return "%s observes %s, also here %s and visible is %s" % (
            self.who,
            self.details,
            self.people,
            self.items,
        )


class Area(Entity):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.owner = kwargs["owner"]
        self.details = kwargs["details"]
        self.here: List[Entity] = []

    def entities(self):
        return self.here

    def contains(self, e: Entity):
        return e in self.here

    def remove(self, e: Entity):
        self.here.remove(e)
        return self

    def look(self, player: Player):
        people = [
            e.observe() for e in self.here if isinstance(e, Person) and e != player
        ]
        items = [e.observe() for e in self.here if isinstance(e, Item)]
        return Observation(player.observe(), self.details, people, items)

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
                "details": self.details.__dict__,
                "owner": self.owner.key,
                "here": [e.key for e in self.entities()],
            }
        )
        return p

    def load(self, world, properties):
        super().load(world, properties)
        self.details.__dict__ = properties["details"]
        self.here = world.resolve(properties["here"])

    def accept(self, visitor: Visitor):
        return visitor.area(self)

    def __str__(self):
        return self.details.name

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


class World(Entity):
    def __init__(self, bus: EventBus):
        self.details = Details("World", "Ya know, everything")
        self.key = "world"
        self.bus = bus
        self.entities = {}

    def register(self, entity: Entity):
        self.entities[entity.key] = entity

    def unregister(self, entity: Entity):
        del self.entities[entity.key]

    def empty(self):
        return len(self.entities.keys()) == 0

    def areas(self):
        return [e for e in self.entities.values() if isinstance(e, Area)]

    def people(self):
        return [e for e in self.entities.values() if isinstance(e, Person)]

    def players(self):
        return [e for e in self.entities.values() if isinstance(e, Player)]

    def welcome_area(self):
        return self.areas()[0]

    def look(self, player: Player):
        area = self.find_player_area(player)
        return area.look(player)

    def find_entity_area(self, entity: Entity):
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
            details=Details(
                "A pristine, new place.",
                "Nothing seems to be here, maybe you should decorate?",
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
        return await action.perform(self, player)


class Action:
    def __init__(self, **kwargs):
        pass

    async def perform(self, world: World, player: Player):
        raise Exception("unimplemented")


class Make(Action):
    def __init__(self, item, **kwargs):
        super().__init__(**kwargs)
        self.item = item

    async def perform(self, world: World, player: Player):
        area = world.find_player_area(player)
        player.hold(self.item)
        world.register(self.item)
        await world.bus.publish(ItemMade(player, area, self.item))
        return self.item


class Eat(Action):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.item = kwargs["item"]

    async def perform(self, world: World, player: Player):
        area = world.find_player_area(player)
        world.unregister(self.item)
        player.drop(self.item)
        await world.bus.publish(ItemEaten(player, area, self.item))
        return self.item


class Drink(Action):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.item = kwargs["item"]

    async def perform(self, world: World, player: Player):
        area = world.find_player_area(player)
        world.unregister(self.item)
        player.drop(self.item)
        await world.bus.publish(ItemDrank(player, area, self.item))
        return self.item


class Drop(Action):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def perform(self, world: World, player: Player):
        area = world.find_player_area(player)
        return await area.drop(world.bus, player)


class Join(Action):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def perform(self, world: World, player: Player):
        world.register(player)
        await world.bus.publish(PlayerJoined(player))
        await world.welcome_area().entered(world.bus, player)


class Look(Action):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def perform(self, world: World, player: Player):
        return world.look(player)


class Hold(Action):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.item = kwargs["item"]

    async def perform(self, world: World, player: Player):
        area = world.find_player_area(player)

        if player.is_holding(self.item):
            raise AlreadyHolding("you're already holding that")
        if self.item.area and self.item.owner != player:
            raise NotYours("that's not yours")

        area.remove(self.item)
        player.hold(self.item)
        await world.bus.publish(ItemHeld(player, area, self.item))

        return [self.item]


class Go(Action):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.item = kwargs["item"]

    async def perform(self, world: World, player: Player):
        area = world.find_player_area(player)

        # If the person owns this item and they try to go the thing,
        # this is how new areas area created, one of them.
        if self.item.area is None:
            if self.item.owner != player:
                raise SorryError("you can only do that with things you own")
            self.item.area = world.build_new_area(player, area, self.item)

        await world.perform(player, Drop())
        await area.left(world.bus, player)
        await self.item.area.entered(world.bus, player)

        return self.item.area


class Obliterate(Action):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def perform(self, world: World, player: Player):
        area = world.find_player_area(player)
        items = player.drop_all()
        for item in items:
            world.unregister(item)
            await world.bus.publish(ItemObliterated(player, area, item))


class Remember(Action):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def perform(self, world: World, player: Player):
        area = world.find_player_area(player)
        player.memory = area
        return area


class ModifyField(Action):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.item = kwargs["item"]
        self.field = kwargs["field"]
        self.value = kwargs["value"]

    async def perform(self, world: World, player: Player):
        self.item.details.__dict__[self.field] = self.value


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
