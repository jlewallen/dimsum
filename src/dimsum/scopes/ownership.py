from typing import Optional

from model import Entity, Scope


class Ownership(Scope):
    def __init__(self, owner: Optional[Entity] = None, **kwargs):
        super().__init__(**kwargs)
        default_creator = (
            self.ourselves.creator if self.ourselves.creator else self.ourselves
        )
        self.owner = owner if owner else default_creator
