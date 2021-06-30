from typing import List, Any

import abc
import logging
import dataclasses

import model.events as events
import model.entity as entity

import context
import bus

"""
One thing I've considered is to use this as a place for a way to
intercept existing scopes/operations.

So, being able to decorate with something like

@entity.before(carryable.Containing)

And then using that to maintain our state.
"""

log = logging.getLogger("dimsum.scopes")


class Occupying(entity.Scope):
    def __init__(self, area: entity.Entity = None, **kwargs):
        super().__init__(**kwargs)
        self.area = area

    def update(self, area: entity.Entity):
        self.area = area
        self.ourselves.touch()


class Occupyable(entity.Scope):
    def __init__(self, occupied=None, **kwargs):
        super().__init__(**kwargs)
        self.occupied: List[entity.Entity] = occupied if occupied else []
        self.occupancy: int = 100

    def add_living(self, living: entity.Entity) -> entity.Entity:
        assert isinstance(living, entity.Entity)
        self.occupied.append(living)
        with living.make(Occupying) as occupying:
            occupying.update(self.ourselves)
            self.ourselves.touch()
        return living

    def occupying(self, living: entity.Entity) -> bool:
        return living in self.occupied

    async def entered(self, player: entity.Entity):
        assert player not in self.occupied
        self.add_living(player)
        await context.get().publish(
            LivingEnteredArea(living=player, area=self.ourselves)
        )

    async def left(self, player: entity.Entity):
        assert player in self.occupied
        self.occupied.remove(player)
        self.ourselves.touch()
        await context.get().publish(LivingLeftArea(living=player, area=self.ourselves))


@dataclasses.dataclass
class LivingEnteredArea(events.Event):
    living: entity.Entity
    area: entity.Entity


@dataclasses.dataclass
class LivingLeftArea(events.Event):
    living: entity.Entity
    area: entity.Entity
