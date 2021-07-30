from dataclasses import dataclass, field
from typing import Optional

from loggers import get_logger
from model import Entity, Scope, Event
import scopes.carryable as carryable

log = get_logger("dimsum.scopes")


class FieldMergeStrategy:
    def __init__(self, name: str):
        self.name = name

    def merge(self, old_value, new_value):
        return old_value


class SumFields(FieldMergeStrategy):
    def merge(self, old_value, new_value):
        if not old_value:
            return new_value
        if not new_value:
            return old_value
        return float(old_value) + float(new_value)


def merge_dictionaries(left, right, fields):
    merged = {}
    for field in fields:
        old_value = left[field.name] if field.name in left else None
        new_value = right[field.name] if field.name in right else None
        merged[field.name] = field.merge(old_value, new_value)
    return merged


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

Fields = [SumFields(name) for name in NutritionFields]


class Nutrition:
    def __init__(self, properties=None, **kwargs):
        super().__init__()
        self.properties = properties if properties else {}

    def include(self, other: "Nutrition"):
        changes = merge_dictionaries(self.properties, other.properties, Fields)
        log.info("merged %s" % (changes,))
        self.properties.update(changes)


class Medical:
    def __init__(self, nutrition: Optional[Nutrition] = None, **kwargs):
        super().__init__()
        self.nutrition: Nutrition = nutrition if nutrition else Nutrition()


@dataclass
class Edible(Scope):
    nutrition: Nutrition = field(default_factory=Nutrition)
    servings: int = 1

    def modify_servings(self, s: int):
        self.servings = s


@dataclass
class Health(Scope):
    medical: Medical = field(default_factory=Medical)

    async def consume(self, edible: Entity, drink=True, area=None, ctx=None, **kwargs):
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


@dataclass
class ItemEaten(Event):
    living: Entity
    area: Entity
    item: Entity


@dataclass
class ItemDrank(Event):
    living: Entity
    area: Entity
    item: Entity
