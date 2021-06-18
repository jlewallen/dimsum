from typing import List

import abc

import entity


class ApparelMixin(entity.Scope):
    def __init__(self, wearing=None, **kwargs):
        super().__init__(**kwargs)
        self.wearing: List[entity.Entity] = wearing if wearing else []

    def is_wearing(self, item: entity.Entity) -> bool:
        return item in self.wearing

    def wear(self, item: entity.Entity) -> bool:
        self.wearing.append(item)
        return True

    def unwear(self, item: entity.Entity, **kwargs) -> bool:
        self.wearing.remove(item)
        return True
