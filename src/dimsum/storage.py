from typing import Dict, Any, TextIO, Optional

import logging
import dataclasses
import sqlite3

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
            if data:
                log.debug("updating %s", keys.key)
                self.by_key[keys.key] = data
                self.by_gid[keys.gid] = data
            else:
                log.debug("deleting %s", keys.key)
                del self.by_key[keys.key]
                del self.by_gid[keys.gid]

    async def load_by_gid(self, gid: int):
        if gid in self.by_gid:
            return self.by_gid[gid]
        return None

    async def load_by_key(self, key: str):
        if key in self.by_key:
            return self.by_key[key]
        return None


class SqliteStorage:
    def __init__(self, path: str):
        super().__init__()
        self.path = path
        self.db: Optional[sqlite3.Connection] = None
        self.dbc: Optional[sqlite3.Cursor] = None

    async def open_if_necessary(self):
        if self.db:
            return
        self.db = sqlite3.connect(self.path)
        self.dbc = self.db.cursor()
        self.dbc.execute(
            "CREATE TABLE IF NOT EXISTS entities (key TEXT NOT NULL PRIMARY KEY, gid INTEGER NOT NULL, serialized TEXT NOT NULL)"
        )
        self.db.commit()

    async def load_query(self, query: str, args: Any):
        await self.open_if_necessary()
        assert self.db

        self.dbc = self.db.cursor()

        rows = {}
        for row in self.dbc.execute(query, args):
            rows[row[0]] = row[1]

        self.db.rollback()

        return list(rows.values())

    async def write(self, stream: TextIO):
        await self.open_if_necessary()
        assert self.db

        self.dbc = self.db.cursor()
        stream.write("[\n")
        prefix = ""
        for row in self.dbc.execute("SELECT key, serialized FROM entities"):
            stream.write(prefix)
            stream.write(row[1])
            prefix = ","
        stream.write("]\n")

    async def number_of_entities(self):
        await self.open_if_necessary()
        assert self.db

        self.dbc = self.db.cursor()
        return self.dbc.execute("SELECT COUNT(*) FROM entities").fetchone()[0]

    async def purge(self):
        await self.open_if_necessary()
        assert self.db

        self.dbc = self.db.cursor()
        self.dbc.execute("DELETE FROM entities")
        self.db.commit()

    async def destroy(self, keys: Keys):
        await self.open_if_necessary()
        assert self.db

        log.info("destroying %s", keys)
        self.dbc = self.db.cursor()
        self.dbc.execute(
            "DELETE FROM entities WHERE key = ?",
            [
                keys.key,
            ],
        )

    async def update(self, updates: Dict[Keys, Optional[str]]):
        await self.open_if_necessary()
        assert self.db

        self.dbc = self.db.cursor()
        for keys, data in updates.items():
            if data:
                self.dbc.execute(
                    "INSERT INTO entities (key, gid, serialized) VALUES (?, ?, ?) ON CONFLICT(key) DO UPDATE SET gid = EXCLUDED.gid, serialized = EXCLUDED.serialized",
                    [
                        keys.key,
                        keys.gid,
                        data,
                    ],
                )
            else:
                self.dbc.execute(
                    "DELETE FROM entities WHERE key = ?",
                    [
                        keys.key,
                    ],
                )

        self.db.commit()

    async def load_by_gid(self, gid: int):
        loaded = await self.load_query(
            "SELECT key, serialized FROM entities WHERE gid = ?", [gid]
        )
        if len(loaded) == 1:
            return loaded[0]
        return None

    async def load_by_key(self, key: str):
        loaded = await self.load_query(
            "SELECT key, serialized FROM entities WHERE key = ?", [key]
        )
        if len(loaded) == 1:
            return loaded[0]
        return None


class HttpStorage:
    pass
