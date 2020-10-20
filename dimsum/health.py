import logging
import props
import area


log = logging.getLogger("dimsum")


NutritionFields = [
    props.SumFields("sugar"),
    props.SumFields("fat"),
    props.SumFields("protein"),
    props.SumFields("toxicity"),
    props.SumFields("caffeine"),
    props.SumFields("alcohol"),
    props.SumFields("nutrition"),
    props.SumFields("vitamins"),
]


class Nutrition:
    def __init__(self, properties=None, **kwargs):
        super().__init__(**kwargs)  # type: ignore
        self.properties = properties if properties else {}

    def include(self, other: "Nutrition"):
        changes = props.merge_dictionaries(
            self.properties, other.properties, NutritionFields
        )
        log.info("merged %s" % (changes,))
        self.properties.update(changes)


class Medical:
    def __init__(self, nutrition: Nutrition = None, **kwargs):
        super().__init__(**kwargs)  # type: ignore
        self.nutrition = nutrition if nutrition else Nutrition()


class EdibleMixin:
    def __init__(self, nutrition: Nutrition = None, **kwargs):
        super().__init__(**kwargs)  # type: ignore
        self.nutrition = nutrition if nutrition else Nutrition()


class HealthMixin:
    def __init__(self, medical=None, **kwargs):
        super().__init__(**kwargs)  # type: ignore
        self.medical = medical if medical else Medical()

    async def consume(
        self, edible: EdibleMixin, area=None, registrar=None, bus=None, **kwargs
    ):
        self.medical.nutrition.include(edible.nutrition)

        await bus.publish(ItemEaten(self, area, edible))


class ItemEaten:
    def __init__(self, player, area: area.Area, item: EdibleMixin):
        super().__init__()
        self.player = player
        self.area = area
        self.item = item

    def __str__(self):
        return "%s just ate %s!" % (self.player, self.item)


class ItemDrank:
    def __init__(self, player, area: area.Area, item: EdibleMixin):
        self.player = player
        self.area = area
        self.item = item

    def __str__(self):
        return "%s just drank %s!" % (self.player, self.item)
