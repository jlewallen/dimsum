from typing import cast
import logging
import props
import envo
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

Fields = [props.SumFields(name) for name in NutritionFields]


class Nutrition:
    def __init__(self, properties=None, **kwargs):
        super().__init__(**kwargs)  # type: ignore
        self.properties = properties if properties else {}

    def include(self, other: "Nutrition"):
        changes = props.merge_dictionaries(self.properties, other.properties, Fields)
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


class HealthMixin:
    def __init__(self, medical=None, **kwargs):
        super().__init__(**kwargs)  # type: ignore
        self.medical = medical if medical else Medical()

    @property
    def alive(self) -> living.Alive:
        return cast(living.Alive, self)

    async def consume(self, edible: EdibleMixin, area=None, ctx=None, **kwargs):
        self.medical.nutrition.include(edible.nutrition)
        edible.servings -= 1
        if edible.servings == 0:
            self.alive.drop(edible)  # type: ignore
            edible.destroy()  # type:ignore
        await ctx.publish(ItemEaten(self, area, edible))


class ItemEaten:
    def __init__(self, player, area: envo.Area, item: EdibleMixin):
        super().__init__()
        self.player = player
        self.area = area
        self.item = item

    def __str__(self):
        return "%s just ate %s!" % (self.player, self.item)


class ItemDrank:
    def __init__(self, player, area: envo.Area, item: EdibleMixin):
        self.player = player
        self.area = area
        self.item = item

    def __str__(self):
        return "%s just drank %s!" % (self.player, self.item)
