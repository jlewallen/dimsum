from typing import Optional, List, Sequence, Any, cast
import logging
import entity
import context
import living
import apparel
import health
import carryable

log = logging.getLogger("dimsum")


class HealthyAndClothedAnimal(
    context.FindItemMixin,
    living.Alive,
    apparel.ApparelMixin,
    health.HealthMixin,
):
    def gather_entities_under(self) -> List[entity.Entity]:
        return entity.entities(self.holding) + entity.entities(self.wearing)


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
