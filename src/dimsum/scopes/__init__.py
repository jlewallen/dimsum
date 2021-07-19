import logging
from typing import Callable, Optional, Type

from model import Entity, EntityClass

import scopes.behavior as behavior
import scopes.carryable as carryable
import scopes.health as health
import scopes.mechanics as mechanics
import scopes.movement as movement
import scopes.occupyable as occupyable
import scopes.ownership as ownership

log = logging.getLogger("dimsum.scopes")


class LivingClass(EntityClass):
    pass


class ItemClass(EntityClass):
    pass


class AreaClass(EntityClass):
    pass


class ExitClass(EntityClass):
    pass


class ServiceClass(EntityClass):
    pass


Alive = [
    ownership.Ownership,
    behavior.Behaviors,
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
Service = [
    ownership.Ownership,
    behavior.Behaviors,
]

scopes_by_class = {
    LivingClass: Alive,
    ItemClass: Item,
    AreaClass: Area,
    ExitClass: Exit,
    ServiceClass: Service,
}


def _identity(value):
    return value


proxy_factory: Callable = _identity


def set_proxy_factory(factory: Callable):
    global proxy_factory
    previous = proxy_factory
    proxy_factory = factory
    return previous


def create_klass(
    desired: Type[EntityClass], klass: Optional[Type[EntityClass]] = None, **kwargs
) -> Entity:
    assert klass is None  # or klass is desired
    entity_scopes = Item
    if desired in scopes_by_class:
        entity_scopes = scopes_by_class[desired]
    return proxy_factory(
        Entity(create_scopes=entity_scopes, klass=desired, **kwargs)
    )  # TODO create


def alive(**kwargs) -> Entity:
    return create_klass(LivingClass, **kwargs)


def item(klass=None, **kwargs) -> Entity:
    return create_klass(klass if klass else ItemClass, **kwargs)


def area(**kwargs) -> Entity:
    return create_klass(AreaClass, **kwargs)


def exit(**kwargs) -> Entity:
    return create_klass(ExitClass, **kwargs)


classes = {
    "ItemClass": ItemClass,
    "AreaClass": AreaClass,
    "ExitClass": ExitClass,
    "LivingClass": LivingClass,
}


def get_entity_class(name: str) -> Type[EntityClass]:
    assert name in classes
    return classes[name]
