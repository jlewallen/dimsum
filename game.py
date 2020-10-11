from typing import List, Tuple

import logging
import sys


class Entity:
    def describes(self, q: str):
        return False


class Event:
    pass


class EventBus:
    def publish(self, event: Event):
        logging.info("publish:%s", event)


class Details:
    def __init__(self, name: str, desc: str = ""):
        self.name = name
        self.desc = desc

    def __str__(self):
        return self.name


class Activity:
    pass


class Item(Entity):
    def __init__(self, details: Details):
        super().__init__()
        self.details = details

    def describes(self, q: str):
        return q.lower() in self.details.name.lower()

    def observe(self):
        return ObservedItem(self)

    def __str__(self):
        return self.details.name


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
        return "holding a %s" % (self.item,)

    def __repr__(self):
        return str(self)


class Person(Entity):
    def __init__(self):
        super().__init__()
        self.holding: List[Entity] = []

    def observe(self):
        activities = [Holding(e) for e in self.holding if isinstance(e, Item)]
        return ObservedPerson(self, activities)

    def hold(self, item: Item):
        self.holding.append(item)
        return True

    def drop(self, item: Item):
        if item in self.holding:
            self.holding.remove(item)
            return True
        return False


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
    def __init__(self, details: Details):
        super().__init__()
        self.details = details

    def __str__(self):
        return self.details.name


class Route:
    def __init__(self):
        pass


class Observation:
    def __init__(
        self,
        who: Player,
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


class Area:
    def __init__(self, owner: Entity, details: Details, routes=[]):
        self.owner = owner
        self.details = details
        self.routes = routes
        self.navigable = True
        self.here: List[Entity] = []

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
        return Observation(player, self.details, people, items)

    def entered(self, bus: EventBus, player: Player):
        self.here.append(player)
        bus.publish(PlayerEnteredArea(player, self))
        return self

    def left(self, bus: EventBus, player: Player):
        self.here.remove(player)
        bus.publish(PlayerLeftArea(player, self))
        return self

    def add_item(self, item: Item):
        self.here.append(item)
        return self

    def add_route(self, route: Route):
        self.routes.append(route)
        return self

    def find(self, q: str):
        for entity in self.here:
            if entity.describes(q):
                return entity
        return None

    def __str__(self):
        return self.details.name


class World(Entity):
    def __init__(self, bus: EventBus):
        self.bus = bus
        self.areas = []
        self.players = []

    def welcome_area(self):
        return self.areas[0]

    def join(self, player: Player):
        self.players.append(player)
        self.bus.publish(PlayerJoined(player))
        self.welcome_area().entered(self.bus, player)

    def go(self, player: Player, where: str):
        pass

    def quit(self, player: Player):
        self.bus.publish(PlayerQuit(player))
        self.players.remove(player)

    def look(self, player: Player):
        area = self.find_player_area(player)
        return area.look(player)

    def add_area(self, area: Area):
        self.areas.append(area)

    def find_entity_area(self, entity: Entity):
        for area in self.areas:
            if area.contains(entity):
                return area
        return None

    def find_player_area(self, player: Player):
        return self.find_entity_area(player)

    def give(self, player: Player, giving: str, receiving: str):
        pass

    def hold(self, player: Player, q: str):
        area = self.find_player_area(player)
        item = area.find(q)
        if not item:
            return False
        area.remove(item)
        player.hold(item)
        self.bus.publish(ItemHeld(player, area, item))
        return True

    def drop(self, player: Player, q: str):
        pass


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


class ItemDropped(Event):
    def __init__(self, player: Player, area: Area, item: Item):
        self.player = player
        self.area = area
        self.item = item

    def __str__(self):
        return "%s dropped %s" % (self.player, self.item)


if __name__ == "__main__":
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)

    jacob = Player(Details("Jacob", "Curly haired bastard."))
    carla = Player(Details("Carla", "Chief salad officer."))
    hammer = Item(Details("Hammer", "It's heavy."))

    bus = EventBus()
    world = World(bus)
    world.add_area(Area(jacob, Details("Living room")).add_item(hammer))
    world.add_area(Area(jacob, Details("Kitchen")))
    world.join(jacob)
    world.join(carla)

    logging.info(world.look(jacob))
    logging.info(world.look(carla))

    world.hold(jacob, "hammer")

    logging.info(world.look(jacob))
    logging.info(world.look(carla))

    world.give(jacob, "carla", "hammer")
