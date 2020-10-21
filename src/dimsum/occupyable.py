from typing import List, Any

import abc
import bus


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

    async def entered(self, bus: bus.EventBus, player: Living):
        self.occupied.append(player)
        await bus.publish(LivingEnteredArea(player, self))

    async def left(self, bus: bus.EventBus, player: Living):
        self.occupied.remove(player)
        await bus.publish(LivingLeftArea(player, self))


class LivingEnteredArea:
    def __init__(self, living, area):
        super().__init__()
        self.living = living
        self.area = area

    def __str__(self):
        return "%s entered %s" % (self.living, self.area)


class LivingLeftArea:
    def __init__(self, living, area):
        super().__init__()
        self.living = living
        self.area = area

    def __str__(self):
        return "%s left %s" % (self.living, self.area)
