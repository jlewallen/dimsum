import logging
from typing import Callable, Optional, Type

import model.entity as entity
import model.scopes.behavior as behavior
import model.scopes.carryable as carryable
import model.scopes.health as health
import model.scopes.mechanics as mechanics
import model.scopes.movement as movement
import model.scopes.occupyable as occupyable
import model.scopes.ownership as ownership

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


def _identity(value):
    return value


proxy_factory: Callable = _identity


def set_proxy_factory(factory: Callable):
    global proxy_factory
    previous = proxy_factory
    proxy_factory = factory
    return previous


def create_klass(
    desired: Type[entity.EntityClass],
    klass: Optional[Type[entity.EntityClass]] = None,
    **kwargs
) -> entity.Entity:
    assert klass is None or klass is desired
    return proxy_factory(
        entity.Entity(scopes=scopes_by_class[desired], klass=desired, **kwargs)
    )  # TODO create


def alive(**kwargs) -> entity.Entity:
    return create_klass(LivingClass, **kwargs)


def item(**kwargs) -> entity.Entity:
    return create_klass(ItemClass, **kwargs)


def area(**kwargs) -> entity.Entity:
    return create_klass(AreaClass, **kwargs)


def exit(**kwargs) -> entity.Entity:
    return create_klass(ExitClass, **kwargs)


classes = {
    "ItemClass": ItemClass,
    "AreaClass": AreaClass,
    "ExitClass": ExitClass,
    "LivingClass": LivingClass,
}


def get_entity_class(name: str) -> Type[entity.EntityClass]:
    assert name in classes
    return classes[name]
