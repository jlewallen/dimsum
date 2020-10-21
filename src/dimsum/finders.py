from typing import Any, Optional, cast
import logging
import things
import animals

log = logging.getLogger("dimsum")


class HeldItem(things.ItemFinder):
    def __init__(self, q: str = ""):
        super().__init__()
        self.q = q

    def find_item(
        self, person: animals.Person = None, **kwargs
    ) -> Optional[things.Item]:
        assert person
        item = person.find(self.q)
        if item:
            return cast(things.Item, item)
        return None


class ContainedItem(things.ItemFinder):
    def __init__(self, q: str = ""):
        super().__init__()
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
