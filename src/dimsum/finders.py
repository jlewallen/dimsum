from typing import Any, List, Optional, cast
import logging
import things
import animals
import carryable
import envo

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

        item = person.find_item_under(q=self.q, **kwargs)
        if item:
            assert isinstance(item, things.Item)
            return cast(things.Item, item)

        item = area.find_item_under(q=self.q, **kwargs)
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

        item = area.find_item_under(q=self.q)
        if item:
            assert isinstance(item, things.Item)
            return cast(things.Item, item)
        item = person.find_item_under(q=self.q)
        if item:
            assert isinstance(item, things.Item)
            return cast(things.Item, item)
        return None


class AnyHeldItem(things.ItemFinder):
    def find_item(
        self, person: animals.Person = None, **kwargs
    ) -> Optional[things.Item]:
        assert person
        return cast(things.Item, person.find_item_under(**kwargs))


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
        item = person.find_item_under(q=self.q, **kwargs)
        if item:
            assert isinstance(item, things.Item)
            return cast(things.Item, item)
        return None


class FindHeldContainer(things.ItemFinder):
    def find_item(
        self, person: animals.Person = None, **kwargs
    ) -> Optional[things.Item]:
        assert person
        item = person.find_item_under(**kwargs)
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
        for item in things.expected(person.holding):
            for contained in things.expected(item.holding):
                if contained.describes(self.q):
                    return contained
        return None


class MaybeItemOrRecipe:
    def __init__(self, q: str = ""):
        super().__init__()
        assert q
        self.q = q

    def create_item(self, person: animals.Person = None, **kwargs) -> things.Item:
        assert person
        recipe = cast(things.Recipe, person.find_memory(self.q))
        if recipe:
            return things.RecipeItem(recipe).create_item(person=person, **kwargs)
        return things.MaybeItem(self.q).create_item(person=person, **kwargs)
