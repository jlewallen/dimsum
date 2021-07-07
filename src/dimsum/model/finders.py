import logging
from typing import List, Optional

import context
import model.entity as entity
import model.scopes.apparel as apparel
import model.scopes.carryable as carryable
import model.scopes.mechanics as mechanics
import model.scopes.occupyable as occupyable
import model.things as things

log = logging.getLogger("dimsum.model")


class FindNone(things.ItemFinder):
    async def find_item(self, **kwargs) -> Optional[entity.Entity]:
        return None


class StaticItem(things.ItemFinder):
    def __init__(self, item: Optional[entity.Entity] = None, **kwargs):
        super().__init__()
        self.item = item

    async def find_item(self, **kwargs) -> Optional[entity.Entity]:
        return self.item


class ObjectNumber(things.ItemFinder):
    def __init__(self, number: int, **kwargs):
        super().__init__()
        self.number = number

    async def find_item(self, **kwargs) -> Optional[entity.Entity]:
        return await context.get().find_item(number=self.number, **kwargs)


class AnyItem(things.ItemFinder):
    def __init__(self, q: str = ""):
        super().__init__()
        assert q
        self.q = q

    async def find_item(
        self,
        person: Optional[entity.Entity] = None,
        area: Optional[entity.Entity] = None,
        **kwargs
    ) -> Optional[entity.Entity]:
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


class UnheldItem(things.ItemFinder):
    def __init__(self, q: str = ""):
        super().__init__()
        assert q
        self.q = q

    async def find_item(
        self,
        person: Optional[entity.Entity] = None,
        area: Optional[entity.Entity] = None,
        **kwargs
    ) -> Optional[entity.Entity]:
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


class AnyHeldItem(things.ItemFinder):
    async def find_item(
        self, person: Optional[entity.Entity] = None, **kwargs
    ) -> Optional[entity.Entity]:
        assert person

        log.info("%s finding pockets", self)
        with person.make(carryable.Containing) as pockets:
            return await context.get().find_item(candidates=pockets.holding, **kwargs)


class HeldItem(things.ItemFinder):
    def __init__(
        self,
        q: str = "",
    ):
        super().__init__()
        assert q
        self.q = q

    async def find_item(
        self, person: Optional[entity.Entity] = None, **kwargs
    ) -> Optional[entity.Entity]:
        assert person

        log.info("%s finding pockets", self)
        with person.make(carryable.Containing) as pockets:
            item = await context.get().find_item(
                candidates=pockets.holding, q=self.q, **kwargs
            )
            if item:
                return item

        return None


class FindHeldContainer(things.ItemFinder):
    async def find_item(
        self, person: Optional[entity.Entity] = None, **kwargs
    ) -> Optional[entity.Entity]:
        assert person

        log.info("%s finding pockets", self)
        with person.make(carryable.Containing) as pockets:
            item = await context.get().find_item(candidates=pockets.holding, **kwargs)
            if item:
                return item

        return None


class CurrentArea(things.ItemFinder):
    async def find_item(
        self,
        person: Optional[entity.Entity] = None,
        area: Optional[entity.Entity] = None,
        **kwargs
    ) -> Optional[entity.Entity]:
        assert person
        assert area
        return area


class ContainedItem(things.ItemFinder):
    def __init__(self, q: str = ""):
        super().__init__()
        assert q
        self.q = q

    async def find_item(
        self, person: Optional[entity.Entity] = None, **kwargs
    ) -> Optional[entity.Entity]:
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

    def create_item(
        self, person: Optional[entity.Entity] = None, **kwargs
    ) -> entity.Entity:
        assert person

        log.info("%s finding brain", self)
        with person.make(mechanics.Memory) as brain:
            recipe = brain.find_memory(self.q)
            if recipe:
                return things.RecipeItem(recipe).create_item(person=person, **kwargs)

        return things.MaybeItem(self.q).create_item(person=person, **kwargs)
