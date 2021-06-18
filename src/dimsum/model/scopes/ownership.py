from typing import List, Dict

import model.entity as entity


class Ownership(entity.Scope):
    def __init__(self, owner: entity.Entity = None, **kwargs):
        super().__init__(**kwargs)
        self.owner = owner if owner else None

    def constructed(self, creator: entity.Entity = None, **kwargs):
        self.owner = creator if creator else self.ourselves
