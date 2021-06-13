from typing import Optional, List, cast
import logging
import props
import entity
import context
import carryable
import occupyable
import movement
import mechanics
import things

log = logging.getLogger("dimsum")


class Area(
    context.FindItemMixin,
    entity.Entity,
    carryable.ContainingMixin,
    occupyable.OccupyableMixin,
    movement.MovementMixin,
    movement.Area,
    mechanics.Memorable,
    mechanics.WeatherMixin,
):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def gather_entities(self) -> List[entity.Entity]:
        log.debug("area-gather-entities: %s", self)
        return self.entities()

    def entities(self) -> List[entity.Entity]:
        return [cast(things.Item, e) for e in flatten([self.holding, self.occupied])]

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

    def adjacent(self) -> List[movement.Area]:
        # This is here instead of in movement because we access
        # `self.holding` I think once we have a mechanism to
        # optionally get associated entities this will be ok.
        via_routes = super().adjacent()
        via_items = [
            r.area
            for r in flatten(
                [e.available_routes for e in things.expected(self.holding)]
            )
        ]
        return [a for a in flatten([via_routes, via_items])]

    def __str__(self):
        return self.details.name

    def __repr__(self):
        return str(self)


def flatten(l):
    return [item for sl in l for item in sl]
