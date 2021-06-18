from typing import Any, List, Optional, cast
import logging
import things
import animals
import carryable
import context
import envo
import world
import mechanics
import apparel

log = logging.getLogger("dimsum")


class FindNone(things.ItemFinder):
    def find_item(self, **kwargs) -> Optional[things.Item]:
        return None


class StaticItem(things.ItemFinder):
    def __init__(self, item: things.Item = None, **kwargs):
        super().__init__()
        self.item = item

    def find_item(self, **kwargs) -> Optional[things.Item]:
        return self.item


class ObjectNumber(things.ItemFinder):
    def __init__(self, number: int, **kwargs):
        super().__init__()
        self.number = number

    def find_item(self, world: world.World = None, **kwargs) -> Optional[things.Item]:
        assert world
        return cast(things.Item, world.find_by_number(self.number))


class AnyItem(things.ItemFinder):
    def __init__(self, q: str = ""):
        super().__init__()
        assert q
        self.q = q

    def find_item(
        self, person: animals.Person = None, area: envo.Area = None, **kwargs
    ) -> Optional[things.Item]:
        assert person
        assert area

        log.info("%s finding wearing", self)
        with person.make(apparel.ApparelMixin) as wearing:
            item = context.get().find_item(
                candidates=wearing.wearing, q=self.q, **kwargs
            )
            if item:
                assert isinstance(item, things.Item)
                return cast(things.Item, item)

        log.info("%s finding pockets (contained)", self)
        for item in things.expected(person.make(carryable.ContainingMixin).holding):
            for contained in things.expected(
                item.make(carryable.ContainingMixin).holding
            ):
                if contained.describes(q=self.q):
                    return contained

        log.info("%s finding pockets", self)
        with person.make(carryable.ContainingMixin) as pockets:
            item = context.get().find_item(
                candidates=pockets.holding, q=self.q, **kwargs
            )
            if item:
                assert isinstance(item, things.Item)
                return cast(things.Item, item)

        log.info("%s finding ground", self)
        with area.make(carryable.ContainingMixin) as ground:
            item = context.get().find_item(
                candidates=ground.holding, q=self.q, **kwargs
            )
            if item:
                assert isinstance(item, things.Item)
                return cast(things.Item, item)

        return None


class AnyConsumableItem(AnyItem):
    pass


class UnheldItem(things.ItemFinder):
    def __init__(self, q: str = ""):
        super().__init__()
        assert q
        self.q = q

    def find_item(
        self, person: animals.Person = None, area: envo.Area = None, **kwargs
    ) -> Optional[things.Item]:
        assert person
        assert area

        log.info("%s finding area", self)
        with area.make(carryable.ContainingMixin) as contain:
            item = context.get().find_item(candidates=contain.holding, q=self.q)
            if item:
                assert isinstance(item, things.Item)
                return cast(things.Item, item)

        log.info("%s finding pockets", self)
        with person.make(carryable.ContainingMixin) as pockets:
            item = context.get().find_item(candidates=pockets.holding, q=self.q)
            if item:
                assert isinstance(item, things.Item)
                return cast(things.Item, item)

        return None


class AnyHeldItem(things.ItemFinder):
    def find_item(
        self, person: animals.Person = None, **kwargs
    ) -> Optional[things.Item]:
        assert person

        log.info("%s finding pockets", self)
        with person.make(carryable.ContainingMixin) as pockets:
            return context.get().find_item(candidates=pockets.holding, **kwargs)


class HeldItem(things.ItemFinder):
    def __init__(
        self,
        q: str = "",
    ):
        super().__init__()
        assert q
        self.q = q

    def find_item(
        self, person: animals.Person = None, **kwargs
    ) -> Optional[things.Item]:
        assert person

        log.info("%s finding pockets", self)
        with person.make(carryable.ContainingMixin) as pockets:
            item = context.get().find_item(
                candidates=pockets.holding, q=self.q, **kwargs
            )
            if item:
                assert isinstance(item, things.Item)
                return cast(things.Item, item)

        return None


class FindHeldContainer(things.ItemFinder):
    def find_item(
        self, person: animals.Person = None, **kwargs
    ) -> Optional[things.Item]:
        assert person

        log.info("%s finding pockets", self)
        with person.make(carryable.ContainingMixin) as pockets:
            item = context.get().find_item(candidates=pockets.holding, **kwargs)
            if item:
                assert isinstance(item, things.Item)
                return cast(things.Item, item)

        return None


class ContainedItem(things.ItemFinder):
    def __init__(self, q: str = ""):
        super().__init__()
        assert q
        self.q = q

    def find_item(
        self, person: animals.Person = None, **kwargs
    ) -> Optional[things.Item]:
        assert person

        log.info("%s finding pockets (contained)", self)
        for item in things.expected(person.make(carryable.ContainingMixin).holding):
            for contained in things.expected(
                item.make(carryable.ContainingMixin).holding
            ):
                if contained.describes(q=self.q):
                    return contained

        return None


class MaybeItemOrRecipe:
    def __init__(self, q: str = ""):
        super().__init__()
        assert q
        self.q = q

    def create_item(self, person: animals.Person = None, **kwargs) -> things.Item:
        assert person

        log.info("%s finding brain", self)
        with person.make(mechanics.MemoryMixin) as brain:
            recipe = cast(things.Recipe, brain.find_memory(self.q))
            if recipe:
                return things.RecipeItem(recipe).create_item(person=person, **kwargs)

        return things.MaybeItem(self.q).create_item(person=person, **kwargs)
