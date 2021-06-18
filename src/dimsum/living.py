from typing import List, Optional
import logging
import entity
import occupyable
import carryable
import apparel
import mechanics
import scopes


class Activity:
    pass


class HoldingActivity(Activity):
    def __init__(self, item: entity.Entity):
        super().__init__()
        self.item = item

    def __str__(self):
        return "holding %s" % (self.item,)


class Alive(
    entity.Entity,
    occupyable.Living,
    carryable.CarryingMixin,
):
    def __init__(self, **kwargs):
        super().__init__(scopes=scopes.Alive, **kwargs)

    @property
    def quantity(self):
        return 1

    def describes(self, q: str = None, **kwargs) -> bool:
        assert q
        return q.lower() in self.props.name.lower()
