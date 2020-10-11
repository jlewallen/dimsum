class Id:
    def __init__(self, value):
        self.value = value


counter = 0


def id():
    global counter
    counter += 1
    return Id(
        "id-%d" % (counter),
    )


class Entity:
    pass


class World(Entity):
    def __init__(self, players=[], areas=[]):
        self.areas = areas
        self.players = players

    def welcome_area(self):
        return self.areas[0]

    def join(self, player):
        self.players.append(player)
        self.welcome_area().entered(player)
        self.emit("joined", player)

    def add_area(self, area):
        self.areas.append(area)

    def emit(self, name, arg):
        print("emit:" + name, arg)


class Player(Entity):
    def __init__(self, name: str):
        self.name = name


class Item(Entity):
    def __init__(self):
        pass


class Details:
    def __init__(self, name: str):
        self.name = name


class Area:
    def __init__(self, owner: Entity, details: Details, routes=[]):
        self.owner = owner
        self.details = details
        self.routes = routes
        self.here = []

    def entered(self, player: Player):
        self.here.append(player)

    def left(self, player: Player):
        self.here.remove(player)


class Route:
    def __init__(self, target):
        self.target = target


class WorldEvents:
    pass


class Event:
    pass


class PlayerJoined(Event):
    pass


class PlayerQuit(Event):
    pass


class PlayerEnteredArea(Event):
    pass


class PlayerLeftArea(Event):
    pass


if __name__ == "__main__":
    jacob = Player("Jacob")
    carla = Player("Carla")

    world = World()
    world.add_area(Area(jacob, "Living Room", "A simple room."))
    world.add_area(Area(jacob, "Kitchen", "A kitchen."))
    world.join(jacob)
    world.join(carla)
