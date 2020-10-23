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
    def find_item_under(self, **kwargs) -> Optional[carryable.CarryableMixin]:
        return carryable.find_item_under(
            candidates=self.holding + carryable.expected(self.wearing), **kwargs
        )


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
