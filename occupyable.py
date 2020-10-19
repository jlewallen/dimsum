from typing import List, Any

import abc


class Living:
    pass


class OccupyableMixin:
    def __init__(self, occupied=None, **kwargs):
        super().__init__(**kwargs)
        self.occupied: List[Living] = occupied if occupied else []

    def add_living(self, living: Living) -> Living:
        self.occupied.append(living)
        return living

    def occupying(self, living: Living) -> bool:
        return living in self.occupied

    async def entered(self, bus, player):
        self.occupied.append(player)
        await bus.publish(PlayerEnteredArea(player, self))

    async def left(self, bus, player):
        self.occupied.remove(player)
        await bus.publish(PlayerLeftArea(player, self))


class PlayerEnteredArea:
    def __init__(self, player, area):
        super().__init__()
        self.player = player
        self.area = area

    def __str__(self):
        return "%s entered %s" % (self.player, self.area)


class PlayerLeftArea:
    def __init__(self, player, area):
        super().__init__()
        self.player = player
        self.area = area

    def __str__(self):
        return "%s left %s" % (self.player, self.area)
