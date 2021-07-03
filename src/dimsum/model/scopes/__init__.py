from typing import Type

import logging

import model.entity as entity
import model.world as world

import model.scopes.ownership as ownership
import model.scopes.health as health
import model.scopes.mechanics as mechanics
import model.scopes.occupyable as occupyable
import model.scopes.carryable as carryable
import model.scopes.movement as movement
import model.scopes.behavior as behavior

log = logging.getLogger("dimsum.scopes")


class LivingClass(entity.EntityClass):
    pass


class ItemClass(entity.EntityClass):
    pass


class AreaClass(entity.EntityClass):
    pass


class ExitClass(entity.EntityClass):
    pass


Alive = [
    ownership.Ownership,
    carryable.Containing,
    mechanics.Memory,
    health.Health,
]
Item = [ownership.Ownership, behavior.Behaviors, carryable.Carryable]
Exit = [ownership.Ownership, behavior.Behaviors, movement.Exit]
Area = [
    ownership.Ownership,
    behavior.Behaviors,
    carryable.Containing,
    occupyable.Occupyable,
]
World = [ownership.Ownership, behavior.Behaviors]

scopes_by_class = {
    LivingClass: Alive,
    ItemClass: Item,
    AreaClass: Area,
    ExitClass: Exit,
}


def create_klass(klass: Type[entity.EntityClass], **kwargs) -> entity.Entity:
    return entity.Entity(scopes=scopes_by_class[klass], klass=klass, **kwargs)


def alive(**kwargs) -> entity.Entity:
    return entity.Entity(scopes=Alive, klass=LivingClass, **kwargs)


def item(klass=ItemClass, **kwargs) -> entity.Entity:
    return entity.Entity(scopes=Item, klass=klass, **kwargs)


def area(**kwargs) -> entity.Entity:
    return entity.Entity(scopes=Area, klass=AreaClass, **kwargs)


def exit(**kwargs) -> entity.Entity:
    return entity.Entity(scopes=Exit, klass=ExitClass, **kwargs)


classes = {
    "ItemClass": ItemClass,
    "AreaClass": AreaClass,
    "ExitClass": ExitClass,
    "LivingClass": LivingClass,
}


def get_entity_class(name: str) -> Type[entity.EntityClass]:
    assert name in classes
    return classes[name]
