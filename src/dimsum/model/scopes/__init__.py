import logging

import model.entity as entity
import model.world as world

import model.scopes.ownership as ownership
import model.scopes.health as health
import model.scopes.mechanics as mechanics
import model.scopes.occupyable as occupyable
import model.scopes.carryable as carryable
import model.scopes.movement as movement

log = logging.getLogger("dimsum")

Alive = [
    ownership.Ownership,
    carryable.Containing,
    mechanics.Memory,
    health.Health,
]
Item = [ownership.Ownership, carryable.Carryable]
Exit = [ownership.Ownership, movement.Exit]
Area = [ownership.Ownership, carryable.Containing, occupyable.Occupyable]
World = [ownership.Ownership]


class LivingClass(entity.EntityClass):
    pass


class ItemClass(entity.EntityClass):
    pass


class AreaClass(entity.EntityClass):
    pass


class ExitClass(entity.EntityClass):
    pass


def alive(**kwargs) -> entity.Entity:
    return entity.Entity(scopes=Alive, klass=LivingClass, **kwargs)


def item(klass=ItemClass, **kwargs) -> entity.Entity:
    return entity.Entity(scopes=Item, klass=klass, **kwargs)


def area(**kwargs) -> entity.Entity:
    return entity.Entity(scopes=Area, klass=AreaClass, **kwargs)


def exit(**kwargs) -> entity.Entity:
    return entity.Entity(scopes=Exit, klass=ExitClass, **kwargs)
