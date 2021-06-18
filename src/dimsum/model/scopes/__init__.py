import model.entity as entity
import model.world as world

import model.scopes.ownership as ownership
import model.scopes.health as health
import model.scopes.mechanics as mechanics
import model.scopes.occupyable as occupyable
import model.scopes.carryable as carryable
import model.scopes.movement as movement

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


def alive(**kwargs) -> entity.Entity:
    return entity.Entity(scopes=Alive, **kwargs)


def item(**kwargs) -> entity.Entity:
    return entity.Entity(scopes=Item, **kwargs)


def area(**kwargs) -> entity.Entity:
    return entity.Entity(scopes=Area, **kwargs)


def exit(**kwargs) -> entity.Entity:
    return entity.Entity(scopes=Exit, **kwargs)
