from typing import Dict

import logging
import dataclasses

import model.entity as entity

import storage

log = logging.getLogger("dimsum")


@dataclasses.dataclass(frozen=True)
class Keys:
    key: str
    gid: int


class EntityStorage:
    async def number_of_entities(self) -> int:
        raise NotImplementedError

    async def purge(self):
        raise NotImplementedError

    async def destroy(self, keys: Keys):
        raise NotImplementedError

    async def update(self, updates: Dict[Keys, str]):
        raise NotImplementedError

    async def load_by_gid(self, gid: int):
        raise NotImplementedError

    async def load_by_key(self, key: str):
        raise NotImplementedError


class InMemory(EntityStorage):
    def __init__(self):
        super().__init__()
        self.by_key = {}
        self.by_gid = {}

    async def number_of_entities(self) -> int:
        return len(self.by_key)

    async def purge(self):
        self.by_key = {}
        self.by_gid = {}

    async def destroy(self, keys: Keys):
        del self.by_gid[keys.gid]
        del self.by_key[keys.key]

    async def update(self, updates: Dict[Keys, str]):
        for keys, data in updates.items():
            log.info("updating %s", keys.key)
            self.by_key[keys.key] = data
            self.by_gid[keys.gid] = data

    async def load_by_gid(self, gid: int):
        if gid in self.by_gid:
            return self.by_gid[gid]
        return None

    async def load_by_key(self, key: str):
        if key in self.by_key:
            return self.by_key[key]
        return None


class SqliteStorage:
    pass


class HttpStorage:
    pass
