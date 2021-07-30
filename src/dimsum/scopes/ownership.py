from dataclasses import dataclass, field
from typing import Optional

from model import Entity, Scope


@dataclass
class Ownership(Scope):
    owner: Optional[Entity] = None

    def __post_init__(self):
        if self.owner:
            return
        self.owner = (
            self.ourselves.creator if self.ourselves.creator else self.ourselves
        )


def get_owner(entity: Entity) -> Entity:
    with entity.make_and_discard(Ownership) as owner:
        assert owner.owner
        return owner.owner


def get_owner_key(entity: Entity) -> str:
    return get_owner(entity).key


def set_owner(entity: Entity, new_owner: Entity):
    with entity.make(Ownership) as owner:
        if owner.owner.key != new_owner.key:
            owner.owner = new_owner
            entity.touch()
