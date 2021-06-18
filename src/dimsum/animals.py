from typing import Optional, List, Sequence, Any, cast
import logging
import entity
import context
import living
import apparel
import carryable

log = logging.getLogger("dimsum")


class HealthyAndClothedAnimal(
    context.FindItemMixin,
    living.Alive,
):
    def gather_entities(self) -> List[entity.Entity]:
        log.debug("animal-gather-entities: %s", self)
        return (
            entity.entities(self.make(carryable.ContainingMixin).holding)
            + flatten(
                [
                    e.gather_entities()
                    for e in entity.entities(
                        self.make(carryable.ContainingMixin).holding
                    )
                ]
            )
            + entity.entities(self.make(apparel.ApparelMixin).wearing)
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


def flatten(l):
    return [item for sl in l for item in sl]
