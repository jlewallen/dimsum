import dataclasses
import logging
from typing import Optional

import model.entity as entity
import model.events as events
import model.properties as properties

import scopes.carryable as carryable

log = logging.getLogger("dimsum.scopes")


NutritionFields = [
    "sugar",
    "fat",
    "protein",
    "toxicity",
    "caffeine",
    "alcohol",
    "nutrition",
    "vitamins",
]

Fields = [properties.SumFields(name) for name in NutritionFields]


class Nutrition:
    def __init__(self, properties=None, **kwargs):
        super().__init__()
        self.properties = properties if properties else {}

    def include(self, other: "Nutrition"):
        changes = properties.merge_dictionaries(
            self.properties, other.properties, Fields
        )
        log.info("merged %s" % (changes,))
        self.properties.update(changes)


class Medical:
    def __init__(self, nutrition: Optional[Nutrition] = None, **kwargs):
        super().__init__()
        self.nutrition: Nutrition = nutrition if nutrition else Nutrition()


class Edible(entity.Scope):
    def __init__(
        self, nutrition: Optional[Nutrition] = None, servings: int = 1, **kwargs
    ):
        super().__init__(**kwargs)
        self.nutrition: Nutrition = nutrition if nutrition else Nutrition()
        self.servings: int = servings

    def modify_servings(self, s: int):
        self.servings = s


class Health(entity.Scope):
    def __init__(self, medical=None, **kwargs):
        super().__init__(**kwargs)
        self.medical = medical if medical else Medical()

    async def consume(
        self, edible: entity.Entity, drink=True, area=None, ctx=None, **kwargs
    ):
        with edible.make(Edible) as eating:
            self.medical.nutrition.include(eating.nutrition)
            eating.servings -= 1
            if eating.servings == 0:
                with self.ourselves.make(carryable.Containing) as pockets:
                    pockets.drop(edible)
                # TODO Holding chimera
                eating.ourselves.destroy()
            self.ourselves.touch()
            edible.touch()

        if drink:
            await ctx.publish(ItemDrank(living=self.ourselves, area=area, item=edible))
        else:
            await ctx.publish(ItemEaten(living=self.ourselves, area=area, item=edible))


@dataclasses.dataclass
class ItemEaten(events.Event):
    living: entity.Entity
    area: entity.Entity
    item: entity.Entity


@dataclasses.dataclass
class ItemDrank(events.Event):
    living: entity.Entity
    area: entity.Entity
    item: entity.Entity
