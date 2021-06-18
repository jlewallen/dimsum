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
import scopes

log = logging.getLogger("dimsum")


class Area(
    entity.Entity,
):
    def __init__(self, **kwargs):
        super().__init__(scopes=scopes.Area, **kwargs)

    def accept(self, visitor: entity.EntityVisitor):
        return visitor.area(self)

    def adjacent(self) -> List[entity.Entity]:
        areas: List[entity.Entity] = []
        for e in self.make(carryable.ContainingMixin).holding:
            if e.props.navigable:
                areas.append(e.props.navigable)
        return areas

    def __str__(self):
        return self.props.name


class Exit(movement.Navigable, things.Item):
    def __init__(self, area: Area = None, **kwargs):
        super().__init__(action=movement.NavigationAction.EXIT, **kwargs)
        if area:
            self.props[properties.Navigable] = area
        assert self.props[properties.Navigable]

    def accept(self, visitor: entity.EntityVisitor):
        return visitor.exit(self)


def flatten(l):
    return [item for sl in l for item in sl]
