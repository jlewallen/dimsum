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
    def describe(self) -> str:
        with self.make_and_discard(carryable.CarryableMixin) as carry:
            if carry.quantity > 1:
                return "{0} {1} (#{2})".format(
                    carry.quantity,
                    p.plural(self.props.name, carry.quantity),
                    self.props.gid,
                )
        return "{0} (#{1})".format(p.a(self.props.name), self.props.gid)


class ItemFinder:
    def find_item(self, **kwargs) -> Optional[entity.Entity]:
        raise NotImplementedError


class ItemFactory:
    def create_item(self, **kwargs) -> entity.Entity:
        raise NotImplementedError


class MaybeItem(ItemFactory):
    def __init__(self, name: str):
        super().__init__()
        self.name = name

    def create_item(self, quantity: float = None, **kwargs) -> entity.Entity:
        log.debug("create-item: {0}".format(kwargs))
        original = scopes.item(props=properties.Common(self.name), **kwargs)
        if quantity:
            with original.make(carryable.CarryableMixin) as multiple:
                multiple.quantity = quantity
        return original


class RecipeItem(ItemFactory):
    def __init__(self, recipe: entity.Entity):
        super().__init__()
        self.recipe = recipe

    def create_item(self, **kwargs) -> Item:
        return self.recipe.make(RecipeMixin).create_item(**kwargs)


class MaybeQuantifiedItem(ItemFactory):
    def __init__(self, template: MaybeItem, quantity: float):
        super().__init__()
        self.template: MaybeItem = template
        self.quantity: float = quantity

    def create_item(self, **kwargs) -> entity.Entity:
        return self.template.create_item(quantity=self.quantity, **kwargs)


class RecipeMixin(entity.Scope, ItemFactory):
    def __init__(self, template=None, **kwargs):
        super().__init__(**kwargs)
        self.template = template if template else None

    def constructed(self, template=None, **kwargs):
        if template:
            self.template = template

    def create_item(self, **kwargs) -> entity.Entity:
        assert self.template

        log.info("recipe:creating %s %s (todo:sign)", self.template, kwargs)
        updated = copy.deepcopy(self.template.__dict__)
        updated.update(props=self.template.props.clone(), **kwargs)
        cloned = scopes.item(**updated)
        return cloned


def expected(maybes: Sequence[Any]) -> Sequence[Item]:
    return [cast(Item, e) for e in maybes]


def flatten(l):
    return [item for sl in l for item in sl]
