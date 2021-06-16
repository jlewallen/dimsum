from typing import Any, cast
import logging
import events
import properties
import living
import carryable

log = logging.getLogger("dimsum")


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
        super().__init__(**kwargs)  # type: ignore
        self.properties = properties if properties else {}

    def include(self, other: "Nutrition"):
        changes = properties.merge_dictionaries(
            self.properties, other.properties, Fields
        )
        log.info("merged %s" % (changes,))
        self.properties.update(changes)


class Medical:
    def __init__(self, nutrition: Nutrition = None, **kwargs):
        super().__init__(**kwargs)  # type: ignore
        self.nutrition: Nutrition = nutrition if nutrition else Nutrition()


class EdibleMixin:
    def __init__(self, nutrition: Nutrition = None, servings: int = 1, **kwargs):
        super().__init__(**kwargs)  # type: ignore
        self.nutrition: Nutrition = nutrition if nutrition else Nutrition()
        self.servings: int = servings

    def modify_servings(self, s: int):
        self.servings = s


class HealthMixin:
    def __init__(self, medical=None, **kwargs):
        super().__init__(**kwargs)  # type: ignore
        self.medical = medical if medical else Medical()

    @property
    def alive(self) -> living.Alive:
        return cast(living.Alive, self)

    async def consume(
        self, edible: EdibleMixin, drink=True, area=None, ctx=None, **kwargs
    ):
        self.medical.nutrition.include(edible.nutrition)
        edible.servings -= 1
        if edible.servings == 0:
            self.alive.drop(edible)  # type: ignore
            edible.destroy()  # type:ignore

        if drink:
            await ctx.publish(ItemDrank(animal=self, area=area, item=edible))
        else:
            await ctx.publish(ItemEaten(animal=self, area=area, item=edible))


class ItemEaten(events.Event):
    pass


class ItemDrank(events.Event):
    pass
