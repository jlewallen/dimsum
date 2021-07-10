import logging
import copy
from typing import List, Optional

from model import Entity, Scope, Common, ItemFinder, ItemFactory, context
import scopes.apparel as apparel
import scopes.carryable as carryable
import scopes.mechanics as mechanics
import scopes.occupyable as occupyable
import scopes

log = logging.getLogger("dimsum.model")


class AnyItem(ItemFinder):
    def __init__(self, q: str = ""):
        super().__init__()
        assert q
        self.q = q

    async def find_item(
        self, person: Optional[Entity] = None, area: Optional[Entity] = None, **kwargs
    ) -> Optional[Entity]:
        assert person
        assert area

        log.info("%s finding wearing", self)
        with person.make_and_discard(apparel.Apparel) as wearing:
            item = await context.get().find_item(
                candidates=wearing.wearing, q=self.q, **kwargs
            )
            if item:
                return item

        log.info("%s finding pockets (contained)", self)
        for h in person.make_and_discard(carryable.Containing).holding:
            for contained in h.make(carryable.Containing).holding:
                if contained.describes(q=self.q):
                    return contained

        log.info("%s finding pockets", self)
        with person.make_and_discard(carryable.Containing) as pockets:
            item = await context.get().find_item(
                candidates=pockets.holding, q=self.q, **kwargs
            )
            if item:
                return item

        log.info("%s finding ground", self)
        with area.make_and_discard(carryable.Containing) as ground:
            item = await context.get().find_item(
                candidates=ground.holding, q=self.q, **kwargs
            )
            if item:
                return item

        log.info("%s finding occupyable", self)
        with area.make_and_discard(occupyable.Occupyable) as here:
            item = await context.get().find_item(
                candidates=here.occupied, q=self.q, **kwargs
            )
            if item:
                return item

        return None


class AnyConsumableItem(AnyItem):
    pass


class UnheldItem(ItemFinder):
    def __init__(self, q: str = ""):
        super().__init__()
        assert q
        self.q = q

    async def find_item(
        self, person: Optional[Entity] = None, area: Optional[Entity] = None, **kwargs
    ) -> Optional[Entity]:
        assert person
        assert area

        log.info("%s finding area", self)
        with area.make(carryable.Containing) as contain:
            item = await context.get().find_item(candidates=contain.holding, q=self.q)
            if item:
                return item

        log.info("%s finding pockets", self)
        with person.make(carryable.Containing) as pockets:
            item = await context.get().find_item(candidates=pockets.holding, q=self.q)
            if item:
                return item

        return None


class AnyHeldItem(ItemFinder):
    async def find_item(
        self, person: Optional[Entity] = None, **kwargs
    ) -> Optional[Entity]:
        assert person

        log.info("%s finding pockets", self)
        with person.make(carryable.Containing) as pockets:
            return await context.get().find_item(candidates=pockets.holding, **kwargs)


class HeldItem(ItemFinder):
    def __init__(
        self,
        q: str = "",
    ):
        super().__init__()
        assert q
        self.q = q

    async def find_item(
        self, person: Optional[Entity] = None, **kwargs
    ) -> Optional[Entity]:
        assert person

        log.info("%s finding pockets", self)
        with person.make(carryable.Containing) as pockets:
            item = await context.get().find_item(
                candidates=pockets.holding, q=self.q, **kwargs
            )
            if item:
                return item

        return None


class FindHeldContainer(ItemFinder):
    async def find_item(
        self, person: Optional[Entity] = None, **kwargs
    ) -> Optional[Entity]:
        assert person

        log.info("%s finding pockets", self)
        with person.make(carryable.Containing) as pockets:
            item = await context.get().find_item(candidates=pockets.holding, **kwargs)
            if item:
                return item

        return None


class ContainedItem(ItemFinder):
    def __init__(self, q: str = ""):
        super().__init__()
        assert q
        self.q = q

    async def find_item(
        self, person: Optional[Entity] = None, **kwargs
    ) -> Optional[Entity]:
        assert person

        log.info("%s finding pockets (contained)", self)
        for item in person.make(carryable.Containing).holding:
            for contained in item.make(carryable.Containing).holding:
                if contained.describes(q=self.q):
                    return contained

        return None


class MaybeItemOrRecipe:
    def __init__(self, q: str = ""):
        super().__init__()
        assert q
        self.q = q

    def create_item(self, person: Optional[Entity] = None, **kwargs) -> Entity:
        assert person

        log.info("%s finding brain", self)
        with person.make(mechanics.Memory) as brain:
            recipe = brain.find_memory(self.q)
            if recipe:
                return RecipeItem(recipe).create_item(person=person, **kwargs)

        return MaybeItem(self.q).create_item(person=person, **kwargs)


class MaybeItem(ItemFactory):
    def __init__(self, name: str):
        super().__init__()
        self.name = name

    def create_item(self, quantity: Optional[float] = None, **kwargs) -> Entity:
        log.info(
            "%s create-item '%s' %s quantity=%s", self, self.name, kwargs, quantity
        )
        initialize = {}
        if quantity:
            initialize = {carryable.Carryable: dict(quantity=quantity)}
        return scopes.item(props=Common(self.name), initialize=initialize, **kwargs)


class RecipeItem(ItemFactory):
    def __init__(self, recipe: Entity):
        super().__init__()
        self.recipe = recipe

    def create_item(self, **kwargs) -> Entity:
        log.info("%s create-item recipe=%s %s", self, self.recipe, kwargs)
        return self.recipe.make(Recipe).create_item(**kwargs)


class MaybeQuantifiedItem(ItemFactory):
    def __init__(self, template: MaybeItem, quantity: float):
        super().__init__()
        self.template: MaybeItem = template
        self.quantity: float = quantity

    def create_item(self, **kwargs) -> Entity:
        log.info(
            "%s create-item template=%s quantity=%s %s",
            self,
            self.template,
            self.quantity,
            kwargs,
        )
        return self.template.create_item(quantity=self.quantity, **kwargs)


class Recipe(Scope, ItemFactory):
    def __init__(self, template=None, **kwargs):
        super().__init__(**kwargs)
        self.template = template if template else None

    def create_item(
        self, quantity: Optional[float] = None, initialize=None, **kwargs
    ) -> Entity:
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
