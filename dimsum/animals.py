from typing import Optional
import logging
import entity
import living
import apparel
import health
import carryable

log = logging.getLogger("dimsum")


class HealthyAndClothedAnimal(
    living.Alive,
    apparel.ApparelMixin,
    health.HealthMixin,
):
    def find(self, q: str) -> Optional[carryable.CarryableMixin]:
        e = super().find(q)
        if e:
            return e
        for e in self.wearing:
            if e.describes(q):
                return e
        return None


class Mammal(HealthyAndClothedAnimal):
    pass


class Animal(Mammal):
    def accept(self, visitor: entity.EntityVisitor):
        return visitor.animal(self)


class Person(Mammal):
    def accept(self, visitor: entity.EntityVisitor):
        return visitor.person(self)


class Player(Person):
    pass
