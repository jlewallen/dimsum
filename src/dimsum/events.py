from things import *
from envo import *
from living import *
from animals import *


class Event:
    pass


class PlayerJoined(Event):
    def __init__(self, player: Player):
        super().__init__()
        self.player = player

    def __str__(self):
        return "%s joined" % (self.player)


class PlayerQuit(Event):
    def __init__(self, player: Player):
        super().__init__()
        self.player = player

    def __str__(self):
        return "%s quit" % (self.player)


class AreaConstructed(Event):
    def __init__(self, player: Player, area: Area):
        super().__init__()
        self.player = player
        self.area = area

    def __str__(self):
        return "%s constructed %s" % (self.player, self.area)


class ItemHeld(Event):
    def __init__(self, player: Player, area: Area, item: Item):
        super().__init__()
        self.player = player
        self.area = area
        self.item = item

    def __str__(self):
        return "%s picked up %s" % (self.player, self.item)


class ItemMade(Event):
    def __init__(self, player: Player, area: Area, item: Item):
        super().__init__()
        self.player = player
        self.area = area
        self.item = item

    def __str__(self):
        return "%s created %s out of thin air!" % (self.player, self.item)


class ItemsDropped(Event):
    def __init__(self, player: Player, area: Area, items: List[Item]):
        super().__init__()
        self.player = player
        self.area = area
        self.items = items

    def __str__(self):
        return "%s dropped %s" % (self.player, p.join(self.items))


class ItemObliterated(Event):
    def __init__(self, player: Player, area: Area, item: Item):
        super().__init__()
        self.player = player
        self.area = area
        self.item = item

    def __str__(self):
        return "%s obliterated %s" % (self.player, self.item)
