from typing import Optional

from .entity import Entity
from .context import get


class ItemFinder:
    async def find_item(self, **kwargs) -> Optional[Entity]:
        raise NotImplementedError


class FindNone(ItemFinder):
    async def find_item(self, **kwargs) -> Optional[Entity]:
        return None


class FindStaticItem(ItemFinder):
    def __init__(self, item: Optional[Entity] = None, **kwargs):
        super().__init__()
        self.item = item

    async def find_item(self, **kwargs) -> Optional[Entity]:
        return self.item


class FindObjectByGid(ItemFinder):
    def __init__(self, gid: int, **kwargs):
        super().__init__()
        self.gid = gid

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
