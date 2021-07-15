from typing import Optional

from model import Entity, Scope


class Ownership(Scope):
    def __init__(self, owner: Optional[Entity] = None, **kwargs):
        super().__init__(**kwargs)
        default_creator = (
            self.ourselves.creator if self.ourselves.creator else self.ourselves
        )
        self.owner = owner if owner else default_creator


def get_owner(entity: Entity) -> Entity:
    with entity.make_and_discard(Ownership) as owner:
        assert owner.owner
        return owner.owner


def get_owner_key(entity: Entity) -> str:
    return get_owner(entity).key


def set_owner(entity: Entity, new_owner: Entity):
    with entity.make(Ownership) as owner:
        owner.owner = new_owner
