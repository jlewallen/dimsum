from dataclasses import dataclass, field
from typing import List

from model import Entity, Scope


@dataclass
class Apparel(Scope):
    wearing: List[Entity] = field(default_factory=list)

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
