from typing import Any, Optional, cast
import logging
import things
import animals
import envo

log = logging.getLogger("dimsum")


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

        item = person.find(self.q)
        if item:
            assert isinstance(item, things.Item)
            return cast(things.Item, item)
        item = area.find(self.q)
        if item:
            assert isinstance(item, things.Item)
            return cast(things.Item, item)
        return None


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

        item = area.find(self.q)
        if item:
            assert isinstance(item, things.Item)
            return cast(things.Item, item)
        item = person.find(self.q)
        if item:
            assert isinstance(item, things.Item)
            return cast(things.Item, item)
        return None


class SoloHeldItem(things.ItemFinder):
    def find_item(
        self, person: animals.Person = None, **kwargs
    ) -> Optional[things.Item]:
        assert person
        if len(person.holding) == 0:
            return None
        return person.holding[0]


class HeldItem(things.ItemFinder):
    def __init__(self, q: str = ""):
        super().__init__()
        assert q
        self.q = q

    def find_item(
        self, person: animals.Person = None, **kwargs
    ) -> Optional[things.Item]:
        assert person
        item = person.find(self.q)
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
        for item in person.holding:
            for contained in item.holding:
                if contained.describes(self.q):
                    return contained
        return None


class MaybeItemOrRecipe:
    def __init__(self, q: str = ""):
        super().__init__()
        assert q
        self.q = q

    def create_item(self, person=None, **kwargs) -> things.Item:
        assert person
        recipe = person.find_memory(self.q)
        if recipe:
            return things.RecipeItem(recipe).create_item(person=person, **kwargs)
        return things.MaybeItem(self.q).create_item(person=person, **kwargs)
