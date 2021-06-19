from typing import List, Any

import abc
import bus

import model.events as events
import model.entity as entity


class Occupying(entity.Scope):
    def __init__(self, area: entity.Entity = None, **kwargs):
        super().__init__(**kwargs)
        self.area = area


class Occupyable(entity.Scope):
    def __init__(self, occupied=None, **kwargs):
        super().__init__(**kwargs)
        self.occupied: List[entity.Entity] = occupied if occupied else []
        self.occupancy: int = 100

    def add_living(self, living: entity.Entity) -> entity.Entity:
        self.occupied.append(living)
        with living.make(Occupying) as occupying:
            occupying.area = self.ourselves
        return living

    def occupying(self, living: entity.Entity) -> bool:
        return living in self.occupied

    async def entered(self, bus: bus.EventBus, player: entity.Entity):
        assert player not in self.occupied
        self.add_living(player)
        await bus.publish(LivingEnteredArea(living=player, area=self))

    async def left(self, bus: bus.EventBus, player: entity.Entity):
        assert player in self.occupied
        self.occupied.remove(player)
        await bus.publish(LivingLeftArea(living=player, area=self))


class LivingEnteredArea(events.Event):
    pass


class LivingLeftArea(events.Event):
    pass
