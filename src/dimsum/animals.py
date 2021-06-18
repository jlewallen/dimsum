from typing import Optional, List, Sequence, Any, cast
import logging
import entity
import context
import living
import apparel
import carryable

log = logging.getLogger("dimsum")


class HealthyAndClothedAnimal(
    living.Alive,
):
    pass


class Mammal(HealthyAndClothedAnimal):
    pass


class Animal(Mammal):
    pass


class Person(Mammal):
    pass


class Player(Person):
    pass
