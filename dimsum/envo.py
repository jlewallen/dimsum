from typing import List
import logging
import entity
import carryable
import occupyable
import movement
import mechanics

log = logging.getLogger("dimsum")


class Area(
    entity.Entity,
    carryable.ContainingMixin,
    occupyable.OccupyableMixin,
    movement.MovementMixin,
    movement.Area,
    mechanics.Memorable,
):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @property
    def items(self):
        return self.holding

    def entities(self) -> List[entity.Entity]:
        return flatten([self.holding, self.occupied])

    def entities_named(self, of: str):
        return [e for e in self.entities() if e.describes(of)]

    def entities_of_kind(self, kind: entity.Kind):
        return [e for e in self.entities() if e.kind and e.kind.same(kind)]

    def number_of_named(self, of: str) -> int:
        return sum([e.quantity for e in self.entities_named(of)])

    def number_of_kind(self, kind: entity.Kind) -> int:
        return sum([e.quantity for e in self.entities_of_kind(kind)])

    def accept(self, visitor: entity.EntityVisitor):
        return visitor.area(self)

    def add_item_and_link_back(self, item: carryable.CarryableMixin):
        self.add_item(item)
        copy = item.clone(key=None, identity=None, routes=[])  # type: ignore
        copy.link_area(self)
        other_area = item.require_single_linked_area  # type: ignore
        other_area.add_item(copy)
        return self, other_area

    def __str__(self):
        return self.details.name

    def __repr__(self):
        return str(self)


def flatten(l):
    return [item for sl in l for item in sl]
