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

    def __str__(self):
        return self.props.name


class Exit(entity.Entity, movement.Navigable, entity.IgnoreExtraConstructorArguments):
    def __init__(self, **kwargs):
        super().__init__(scopes=[movement.ExitMixin], **kwargs)


def flatten(l):
    return [item for sl in l for item in sl]
