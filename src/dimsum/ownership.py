from typing import List, Dict

import entity


class Ownership(entity.Spawned):
    def __init__(self, owner: entity.Entity = None, **kwargs):
        super().__init__(**kwargs)
        self.owner = owner if owner else None

    def constructed(self, creator: entity.Entity = None, **kwargs):
        self.owner = creator if creator else self.ourselves
