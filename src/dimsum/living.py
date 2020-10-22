from typing import List, Optional
import logging
import entity
import occupyable
import carryable
import apparel
import mechanics
import health


class Activity:
    pass


class HoldingActivity(Activity):
    def __init__(self, item: entity.Entity):
        super().__init__()
        self.item = item

    def __str__(self):
        return "holding %s" % (self.item,)

    def __repr__(self):
        return str(self)


class Alive(
    entity.Entity,
    occupyable.Living,
    carryable.CarryingMixin,
    mechanics.VisibilityMixin,
    mechanics.MemoryMixin,
):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @property
    def quantity(self):
        return 1

    def describes(self, q: str) -> bool:
        return q.lower() in self.details.name.lower()

    def __str__(self):
        return self.details.name

    def __repr__(self):
        return str(self)
