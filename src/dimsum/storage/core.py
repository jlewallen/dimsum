from typing import Any, Dict, List, Optional

from model import Entity, CompiledJson, Serialized


class EntityStorage:
    async def number_of_entities(self) -> int:
        raise NotImplementedError

    async def update(self, updates: Dict[str, CompiledJson]) -> Dict[str, CompiledJson]:
        raise NotImplementedError

    async def load_by_gid(self, gid: int) -> List[Serialized]:
        raise NotImplementedError

    async def load_by_key(self, key: str) -> List[Serialized]:
        raise NotImplementedError

    async def load_all_keys(self) -> List[str]:
        raise NotImplementedError


class AllStorageChain(EntityStorage):
    def __init__(self, children: List[EntityStorage]):
        super().__init__()
        self.children = children

    async def number_of_entities(self) -> int:
        return max([await child.number_of_entities() for child in self.children])

    async def update(self, diffs: Dict[str, CompiledJson]):
        for child in self.children:
            returning = await child.update(diffs)
        return returning

    async def load_by_gid(self, gid: int) -> List[Serialized]:
        for child in self.children:
            maybe = await child.load_by_gid(gid)
            if maybe:
                return maybe
        return []

    async def load_by_key(self, key: str) -> List[Serialized]:
        for child in self.children:
            maybe = await child.load_by_key(key)
            if maybe:
                return maybe
        return []

    async def load_all_keys(self) -> List[str]:
        return flatten([c.load_all_keys() for c in self.children])

    def __str__(self):
        return "All<{0}>".format(self.children)


class PrioritizedStorageChain(EntityStorage):
    def __init__(self, children: List[EntityStorage]):
        super().__init__()
        self.children = children

    async def number_of_entities(self) -> int:
        for child in self.children:
            return await child.number_of_entities()
        return 0

    async def update(self, diffs: Dict[str, CompiledJson]):
        for child in self.children:
            return await child.update(diffs)

    async def load_by_gid(self, gid: int) -> List[Serialized]:
        for child in self.children:
            maybe = await child.load_by_gid(gid)
            if maybe:
                return maybe
        return []

    async def load_by_key(self, key: str) -> List[Serialized]:
        for child in self.children:
            maybe = await child.load_by_key(key)
            if maybe:
                return maybe
        return []

    async def load_all_keys(self) -> List[str]:
        for child in self.children:
            maybe = await child.load_all_keys()
            if maybe:
                return maybe
        return []

    def __str__(self):
        return "Prioritized<{0}>".format(self.children)


class SeparatedStorageChain(EntityStorage):
    def __init__(self, read: EntityStorage, write: EntityStorage):
        super().__init__()
        self.read = read
        self.write = write

    async def number_of_entities(self) -> int:
        return await self.read.number_of_entities()

    async def update(self, diffs: Dict[str, CompiledJson]):
        return await self.write.update(diffs)

    async def load_by_gid(self, gid: int) -> List[Serialized]:
        return await self.read.load_by_gid(gid)

    async def load_by_key(self, key: str) -> List[Serialized]:
        return await self.read.load_by_key(key)

    async def load_all_keys(self) -> List[str]:
        return await self.read.load_all_keys()

    def __str__(self):
        return "Separated<read={0}, write={1}>".format(self.read, self.write)


def flatten(l):
    return [item for sl in l for item in sl]
