from typing import List, Optional, Any, Sequence, cast

import logging
import copy
import inflect
import properties
import crypto
import entity
import context
import apparel
import carryable
import mechanics
import movement
import health

log = logging.getLogger("dimsum")
p = inflect.engine()


class Item(
    context.FindItemMixin,
    entity.Entity,
    apparel.Wearable,
    carryable.CarryableMixin,
    carryable.ContainingMixin,
    carryable.KeyMixin,
    mechanics.InteractableMixin,
    mechanics.VisibilityMixin,
    movement.MovementMixin,
    health.EdibleMixin,
):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.validate()

    def describes(self, q: str) -> bool:
        if q.lower() in self.props[properties.Name].lower():
            return True
        if q.lower() in str(self).lower():
            return True
        return False

    def gather_entities(self) -> List[entity.Entity]:
        log.debug("item-gather-entities: %s", self)
        return entity.entities(self.holding) + flatten(
            [e.gather_entities() for e in entity.entities(self.holding)]
        )

    def separate(
        self, quantity: int, ctx: context.Ctx = None, **kwargs
    ) -> List["Item"]:
        assert ctx
        self.decrease_quantity(quantity)
        item = Item(
            kind=self.kind,
            props=self.props,
            behaviors=self.behaviors,
            quantity=quantity,
            **kwargs
        )
        # TODO Move to caller
        ctx.registrar().register(item)
        return [item]

    def clone(self, **kwargs):
        updated = copy.copy(self.__dict__)
        updated.update(**kwargs)
        return Item(**updated)

    def accept(self, visitor: entity.EntityVisitor) -> Any:
        return visitor.item(self)

    def __str__(self):
        if self.quantity > 1:
            return "%d %s" % (
                self.quantity,
                p.plural(self.props[properties.Name], self.quantity),
            )
        return p.a(self.props[properties.Name])

    def __repr__(self):
        return str(self)


class ItemFinder:
    def find_item(self, **kwargs) -> Optional[Item]:
        raise NotImplementedError


class ItemFactory:
    def create_item(self, **kwargs) -> Item:
        raise NotImplementedError


class MaybeItem(ItemFactory):
    def __init__(self, name: str):
        super().__init__()
        self.name = name

    def create_item(self, **kwargs) -> Item:
        return Item(props=properties.Common(self.name), **kwargs)


class RecipeItem(ItemFactory):
    def __init__(self, recipe: "Recipe"):
        super().__init__()
        self.recipe = recipe

    def create_item(self, **kwargs) -> Item:
        return self.recipe.create_item(**kwargs)


class MaybeQuantifiedItem(ItemFactory):
    def __init__(self, template: MaybeItem, quantity: float):
        super().__init__()
        self.template: MaybeItem = template
        self.quantity: float = quantity

    def create_item(self, **kwargs) -> Item:
        return self.template.create_item(quantity=self.quantity, **kwargs)


class Recipe(Item, ItemFactory, mechanics.Memorable):
    def __init__(self, template=None, **kwargs):
        super().__init__(**kwargs)
        assert template
        self.template = template.clone()

    def create_item(self, **kwargs) -> Item:
        log.info("recipe:creating %s %s (todo:sign)", self.template, kwargs)
        return self.template.clone(**kwargs)

    def accept(self, visitor: entity.EntityVisitor) -> Any:
        return visitor.recipe(self)


def expected(maybes: Sequence[Any]) -> Sequence[Item]:
    return [cast(Item, e) for e in maybes]


def flatten(l):
    return [item for sl in l for item in sl]
