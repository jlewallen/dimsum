from typing import List, Any

import abc
import bus
import events
import entity


class Living:
    pass


class OccupyableMixin(entity.Scope):
    def __init__(self, occupied=None, **kwargs):
        super().__init__(**kwargs)
        self.occupied: List[Living] = occupied if occupied else []

    def add_living(self, living: Living) -> Living:
        self.occupied.append(living)
        return living

    def occupying(self, living: Living) -> bool:
        return living in self.occupied

    async def entered(self, bus: bus.EventBus, player: Living):
        assert player not in self.occupied
        self.occupied.append(player)
        await bus.publish(LivingEnteredArea(living=player, area=self))

    async def left(self, bus: bus.EventBus, player: Living):
        assert player in self.occupied
        self.occupied.remove(player)
        await bus.publish(LivingLeftArea(living=player, area=self))


class LivingEnteredArea(events.Event):
    pass


class LivingLeftArea(events.Event):
    pass
