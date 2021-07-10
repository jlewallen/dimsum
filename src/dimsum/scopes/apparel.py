from typing import List

from model import Entity, Scope


class Apparel(Scope):
    def __init__(self, wearing=None, **kwargs):
        super().__init__(**kwargs)
        self.wearing: List[Entity] = wearing if wearing else []

    def is_wearing(self, item: Entity) -> bool:
        return item in self.wearing

    def wear(self, item: Entity) -> bool:
        self.wearing.append(item)
        self.ourselves.touch()
        return True

    def unwear(self, item: Entity, **kwargs) -> bool:
        self.wearing.remove(item)
        self.ourselves.touch()
        return True
