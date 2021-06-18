import entity
import ownership
import health
import mechanics
import occupyable
import carryable
import movement
import world

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
