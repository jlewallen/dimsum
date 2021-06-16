from typing import Optional, List, cast
import logging
import enum

import kinds
import properties
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
        return [e for e in flatten([self.holding, self.occupied])]

    def entities_named(self, of: str):
        return [e for e in self.entities() if e.describes(q=of)]

    def entities_of_kind(self, kind: kinds.Kind):
        return [e for e in self.entities() if e.kind and e.kind.same(kind)]

    def number_of_named(self, of: str) -> int:
        return sum([e.quantity for e in self.entities_named(of)])

    def number_of_kind(self, kind: kinds.Kind) -> int:
        return sum([e.quantity for e in self.entities_of_kind(kind)])

    def accept(self, visitor: entity.EntityVisitor):
        return visitor.area(self)

    def adjacent(self) -> List[movement.Area]:
        areas: List[movement.Area] = []
        for e in self.entities():
            if e.props.navigable:
                areas.append(e.props.navigable)
        return areas

    def __str__(self):
        return self.props.name

    def __repr__(self):
        return str(self)


class Exit(movement.Navigable, things.Item):
    def __init__(self, area: Area = None, **kwargs):
        super().__init__(action=movement.NavigationAction.EXIT, **kwargs)
        if area:
            self.props[properties.Navigable] = area
        assert self.props[properties.Navigable]


class Bidirectional:
    def __init__(self, there: Area = None, back: Area = None, **kwargs):
        assert there
        assert back
        goes_there = Exit(
            area=there,
            props=properties.Common(name="Exit to {0}".format(there.props.name)),
            **kwargs
        )
        comes_back = Exit(
            area=back,
            props=properties.Common(name="Exit to {0}".format(back.props.name)),
            **kwargs
        )
        back.add_item(goes_there)
        there.add_item(comes_back)


def flatten(l):
    return [item for sl in l for item in sl]
