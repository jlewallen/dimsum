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
    carryable.ContainingMixin,
    mechanics.MemoryMixin,
    health.HealthMixin,
]
Item = [ownership.Ownership, carryable.CarryableMixin]
Exit = [ownership.Ownership, movement.ExitMixin]
Area = [ownership.Ownership, carryable.ContainingMixin, occupyable.OccupyableMixin]
World = [ownership.Ownership]


def alive(**kwargs) -> entity.Entity:
    return entity.Entity(scopes=Alive, **kwargs)


def item(**kwargs) -> entity.Entity:
    return entity.Entity(scopes=Item, **kwargs)


def area(**kwargs) -> entity.Entity:
    return entity.Entity(scopes=Area, **kwargs)


def exit(**kwargs) -> entity.Entity:
    return entity.Entity(scopes=Exit, **kwargs)
