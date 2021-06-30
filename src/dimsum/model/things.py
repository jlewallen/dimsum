from typing import List, Optional, Any, Sequence, cast

import logging
import copy
import inflect

import model.properties as properties
import model.entity as entity
import model.scopes.carryable as carryable
import model.scopes as scopes

log = logging.getLogger("dimsum.model")
p = inflect.engine()


class ItemFinder:
    async def find_item(self, **kwargs) -> Optional[entity.Entity]:
        raise NotImplementedError


class ItemFactory:
    def create_item(self, **kwargs) -> entity.Entity:
        raise NotImplementedError


class MaybeItem(ItemFactory):
    def __init__(self, name: str):
        super().__init__()
        self.name = name

    def create_item(self, quantity: float = None, **kwargs) -> entity.Entity:
        log.info(
            "%s create-item '%s' %s quantity=%s", self, self.name, kwargs, quantity
        )
        initialize = {}
        if quantity:
            initialize = {carryable.Carryable: dict(quantity=quantity)}
        return scopes.item(
            props=properties.Common(self.name), initialize=initialize, **kwargs
        )


class RecipeItem(ItemFactory):
    def __init__(self, recipe: entity.Entity):
        super().__init__()
        self.recipe = recipe

    def create_item(self, **kwargs) -> entity.Entity:
        log.info("%s create-item recipe=%s %s", self, self.recipe, kwargs)
        return self.recipe.make(Recipe).create_item(**kwargs)


class MaybeQuantifiedItem(ItemFactory):
    def __init__(self, template: MaybeItem, quantity: float):
        super().__init__()
        self.template: MaybeItem = template
        self.quantity: float = quantity

    def create_item(self, **kwargs) -> entity.Entity:
        log.info(
            "%s create-item template=%s quantity=%s %s",
            self,
            self.template,
            self.quantity,
            kwargs,
        )
        return self.template.create_item(quantity=self.quantity, **kwargs)


class Recipe(entity.Scope, ItemFactory):
    def __init__(self, template=None, **kwargs):
        super().__init__(**kwargs)
        self.template = template if template else None

    def create_item(
        self, quantity: float = None, initialize=None, **kwargs
    ) -> entity.Entity:
        assert self.template

        if quantity:
            assert not initialize
            initialize = {carryable.Carryable: dict(quantity=quantity)}

        log.info(
            "%s create-item %s %s initialize=%s",
            self,
            self.template,
            kwargs,
            initialize,
        )
        # TODO Clone
        updated = copy.deepcopy(self.template.__dict__)
        updated.update(
            key=None,
            version=None,
            identity=None,
            props=self.template.props.clone(),
            initialize=initialize,
            **kwargs
        )
        cloned = scopes.item(**updated)
        return cloned
