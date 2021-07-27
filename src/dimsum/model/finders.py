import dataclasses
from typing import Optional

from .entity import Entity
from .context import get


class ItemFinder:
    async def find_item(self, **kwargs) -> Optional[Entity]:
        raise NotImplementedError


class FindNone(ItemFinder):
    async def find_item(self, **kwargs) -> Optional[Entity]:
        return None


@dataclasses.dataclass
class FindStaticItem(ItemFinder):
    item: Entity

    async def find_item(self, **kwargs) -> Optional[Entity]:
        return self.item


@dataclasses.dataclass
class FindObjectByGid(ItemFinder):
    gid: int

    async def find_item(self, **kwargs) -> Optional[Entity]:
        return await get().find_item(number=self.gid, **kwargs)


class FindCurrentArea(ItemFinder):
    async def find_item(
        self, person: Optional[Entity] = None, area: Optional[Entity] = None, **kwargs
    ) -> Optional[Entity]:
        assert person
        assert area
        return area


class ItemFactory:
    def create_item(self, **kwargs) -> Entity:
        raise NotImplementedError


class FindCurrentPerson(ItemFinder):
    async def find_item(
        self, person: Optional[Entity] = None, **kwargs
    ) -> Optional[Entity]:
        assert person
        return person
