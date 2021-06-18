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
import scopes

log = logging.getLogger("dimsum")
p = inflect.engine()


class Item(
    entity.Entity,
    entity.IgnoreExtraConstructorArguments,
):
    def __init__(self, **kwargs):
        super().__init__(scopes=scopes.Item, **kwargs)
        self.validate()

    def describes(self, q: str = None, **kwargs) -> bool:
        if q:
            if q.lower() in self.props[properties.Name].lower():
                return True
            if q.lower() in str(self).lower():
                return True
        return False

    def clone(self, quantity: float = None, **kwargs):
        updated = copy.deepcopy(self.__dict__)
        updated.update(props=self.props.clone(), **kwargs)
        cloned = Item(**updated)
        if quantity:
            with cloned.make(carryable.CarryableMixin) as more:
                more.quantity = quantity
        return cloned

    def accept(self, visitor: entity.EntityVisitor) -> Any:
        return visitor.item(self)

    def __str__(self):
        with self.make_and_discard(carryable.CarryableMixin) as carry:
            if carry.quantity > 1:
                return "%d %s" % (
                    carry.quantity,
                    p.plural(self.props[properties.Name], carry.quantity),
                )
        return p.a(self.props[properties.Name])


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

    def create_item(self, quantity: float = None, **kwargs) -> Item:
        log.debug("create-item: {0}".format(kwargs))
        original = Item(props=properties.Common(self.name), **kwargs)
        if quantity:
            with original.make(carryable.CarryableMixin) as multiple:
                multiple.quantity = quantity
        return original


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
