from typing import List, Tuple

import asyncio
import logging
import sys
import inflect

p = inflect.engine()


class Entity:
    Counter = 0

    def __init__(self):
        Entity.Counter += 1
        self.key = "e-%d" % (Entity.Counter)

    def describes(self, q: str):
        return False

    def saved(self):
        return {
            "key": self.key,
        }

    def load(self, world, properties):
        self.key = properties["key"]


class Event:
    pass


class EventBus:
    async def publish(self, event: Event):
        logging.info("publish:%s", event)


class Details:
    def __init__(self, name: str = "", desc: str = ""):
        self.name = name
        self.desc = desc

    def __str__(self):
        return self.name


class Activity:
    pass


class Item(Entity):
    def __init__(self, owner: Entity, details: Details):
        super().__init__()
        self.owner = owner
        self.details = details

    def describes(self, q: str):
        return q.lower() in self.details.name.lower()

    def observe(self):
        return ObservedItem(self)

    def __str__(self):
        return p.a(self.details.name)

    def saved(self):
        p = super().saved()
        p.update(
            {
                "details": self.details.__dict__,
            }
        )
        return p

    def load(self, world, properties):
        super().load(world, properties)
        self.details.__dict__ = properties["details"]


class ObservedItem:
    def __init__(self, item: Item, where: str = ""):
        self.item = item
        self.where = where

    def __str__(self):
        return self.item

    def __repr__(self):
        return str(self.item)


class Holding(Activity):
    def __init__(self, item: Item):
        super().__init__()
        self.item = item

    def __str__(self):
        return "holding %s" % (self.item,)

    def __repr__(self):
        return str(self)


class Person(Entity):
    def __init__(self, owner: Entity, details: Details):
        super().__init__()
        self.owner = owner
        self.details = details
        self.holding: List[Entity] = []

    def observe(self):
        activities = [Holding(e) for e in self.holding if isinstance(e, Item)]
        return ObservedPerson(self, activities)

    def hold(self, item: Item):
        self.holding.append(item)
        return True

    def drop_all(self):
        dropped = self.holding
        self.holding = []
        return dropped

    def drop(self, item: Item):
        if item in self.holding:
            self.holding.remove(item)
            return True
        return False

    def __str__(self):
        return self.details.name

    def saved(self):
        p = super().saved()
        p.update(
            {
                "details": self.details.__dict__,
                "holding": [e.key for e in self.holding],
            }
        )
        return p

    def load(self, world, properties):
        super().load(world, properties)
        self.details.__dict__ = properties["details"]
        self.holding = world.resolve(properties["holding"])


class ObservedPerson:
    def __init__(self, person: Person, activities: List[Activity]):
        self.person = person
        self.activities = activities

    def __str__(self):
        if len(self.activities) == 0:
            return "%s" % (self.person,)
        return "%s who is %s" % (self.person, self.activities)

    def __repr__(self):
        return str(self)


class Player(Person):
    def __init__(self, owner: Entity, details: Details):
        super().__init__(owner, details)


class Route:
    def __init__(self):
        pass


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
    def __init__(self, owner: Entity, details: Details):
        super().__init__()
        self.owner = owner
        self.details = details
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

    def __str__(self):
        return self.details.name

    async def entered(self, bus: EventBus, player: Player):
        self.here.append(player)
        await bus.publish(PlayerEnteredArea(player, self))
        return self

    async def left(self, bus: EventBus, player: Player):
        self.here.remove(player)
        await bus.publish(PlayerLeftArea(player, self))
        return self

    async def drop(self, bus: EventBus, player: Player):
        for item in player.drop_all():
            self.here.append(item)
            await bus.publish(ItemDropped(player, self, item))
        return self


class World(Entity):
    def __init__(self, bus: EventBus):
        self.key = "world"
        self.bus = bus
        self.entities = {}

    def areas(self):
        return [e for e in self.entities.values() if isinstance(e, Area)]

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

    def resolve(self, keys):
        return [self.entities[key] for key in keys]

    def register(self, entity: Entity):
        self.entities[entity.key] = entity

    def unregister(self, entity: Entity):
        del self.entities[entity.key]

    async def join(self, player: Player):
        self.register(player)
        await self.bus.publish(PlayerJoined(player))
        await self.welcome_area().entered(self.bus, player)

    async def quit(self, player: Player):
        await self.bus.publish(PlayerQuit(player))
        self.unregister(player)

    async def add_area(self, area: Area):
        self.register(area)
        for entity in area.entities():
            self.register(entity)

    async def go(self, player: Player, where: str):
        pass

    async def give(self, player: Player, giving: str, receiving: str):
        pass

    async def hold(self, player: Player, q: str):
        area = self.find_player_area(player)
        item = area.find(q)
        if not item:
            return False
        area.remove(item)
        player.hold(item)
        await self.bus.publish(ItemHeld(player, area, item))
        return True

    async def make(self, player: Player, item: Item):
        area = self.find_player_area(player)
        player.hold(item)
        self.register(item)
        await self.bus.publish(ItemMade(player, area, item))

    async def build(self, player: Player, area: Area):
        await self.bus.publish(AreaConstructed(player, area, item))

    async def drop(self, player: Player):
        area = self.find_player_area(player)
        await area.drop(self.bus, player)


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
        return "%s left" % (self.player, self.area)


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


class ItemDropped(Event):
    def __init__(self, player: Player, area: Area, item: Item):
        self.player = player
        self.area = area
        self.item = item

    def __str__(self):
        return "%s dropped %s" % (self.player, self.item)
