from typing import Optional

import model.entity as entity


class Ownership(entity.Scope):
    def __init__(self, owner: Optional[entity.Entity] = None, **kwargs):
        super().__init__(**kwargs)
        default_creator = (
            self.ourselves.creator if self.ourselves.creator else self.ourselves
        )
        self.owner = owner if owner else default_creator
