from typing import Dict, Any, TextIO, Optional, List

from gql import gql, Client
from gql.transport.aiohttp import AIOHTTPTransport

import logging
import dataclasses
import sqlite3

import model.entity as entity

import storage

log = logging.getLogger("dimsum.storage")


@dataclasses.dataclass(frozen=True)
class Keys:
    key: str
    gid: Optional[int]


class EntityStorage:
    async def number_of_entities(self) -> int:
        raise NotImplementedError

    async def update(self, updates: Dict[Keys, Optional[str]]):
        raise NotImplementedError

    async def load_by_gid(self, gid: int) -> List[entity.Serialized]:
        raise NotImplementedError

    async def load_by_key(self, key: str) -> List[entity.Serialized]:
        raise NotImplementedError


class All(EntityStorage):
    def __init__(self, children: List[EntityStorage]):
        super().__init__()
        self.children = children

    async def number_of_entities(self) -> int:
        return max([await child.number_of_entities() for child in self.children])

    async def update(self, diffs: Dict[Keys, Optional[str]]):
        for child in self.children:
            await child.update(diffs)

    async def load_by_gid(self, gid: int) -> List[entity.Serialized]:
        for child in self.children:
            maybe = await child.load_by_gid(gid)
            if maybe:
                return maybe
        return []

    async def load_by_key(self, key: str) -> List[entity.Serialized]:
        for child in self.children:
            maybe = await child.load_by_key(key)
            if maybe:
                return maybe
        return []

    def __str__(self):
        return "All<{0}>".format(self.children)


class Prioritized(EntityStorage):
    def __init__(self, children: List[EntityStorage]):
        super().__init__()
        self.children = children

    async def number_of_entities(self) -> int:
        for child in self.children:
            return await child.number_of_entities()
        return 0

    async def update(self, diffs: Dict[Keys, Optional[str]]):
        for child in self.children:
            return await child.update(diffs)

    async def load_by_gid(self, gid: int) -> List[entity.Serialized]:
        for child in self.children:
            maybe = await child.load_by_gid(gid)
            if maybe:
                return maybe
        return []

    async def load_by_key(self, key: str) -> List[entity.Serialized]:
        for child in self.children:
            maybe = await child.load_by_key(key)
            if maybe:
                return maybe
        return []

    def __str__(self):
        return "Prioritized<{0}>".format(self.children)


class Separated(EntityStorage):
    def __init__(self, read: EntityStorage, write: EntityStorage):
        super().__init__()
        self.read = read
        self.write = write

    async def number_of_entities(self) -> int:
        return await self.read.number_of_entities()

    async def update(self, diffs: Dict[Keys, Optional[str]]):
        return await self.write.update(diffs)

    async def load_by_gid(self, gid: int) -> List[entity.Serialized]:
        return await self.read.load_by_gid(gid)

    async def load_by_key(self, key: str) -> List[entity.Serialized]:
        return await self.read.load_by_key(key)

    def __str__(self):
        return "Separated<read={0}, write={1}>".format(self.read, self.write)


class InMemory(EntityStorage):
    def __init__(self):
        super().__init__()
        log.info("%s constructed!", self)
        self.by_key = {}
        self.by_gid = {}
        self.gid_to_key = {}

    async def number_of_entities(self) -> int:
        return len(self.by_key)

    async def purge(self):
        log.info("%s purge!", self)
        self.by_key = {}
        self.by_gid = {}
        self.gid_to_key = {}

    async def update(self, updates: Dict[Keys, Optional[str]]):
        for keys, data in updates.items():
            if data:
                log.debug("updating %s", keys.key)
                self.by_key[keys.key] = data
                self.by_gid[keys.gid] = data
                self.gid_to_key[keys.gid] = keys.key
            else:
                if keys.key in self.by_key:
                    log.debug("deleting %s", keys.key)
                    del self.by_key[keys.key]
                else:
                    log.warning("delete:noop %s", keys.key)

                if keys.gid in self.by_gid:
                    del self.by_gid[keys.gid]
                    del self.gid_to_key[keys.gid]

    async def load_by_gid(self, gid: int):
        if gid in self.by_gid:
            key = self.gid_to_key[gid]
            return [entity.Serialized(key, self.by_gid[gid])]
        return []

    async def load_by_key(self, key: str):
        if key in self.by_key:
            return [entity.Serialized(key, self.by_key[key])]
        return []

    async def write(self, stream: TextIO):
        stream.write("[\n")
        prefix = ""
        for key, item in self.by_key.items():
            stream.write(prefix)
            stream.write(item)
            prefix = ","
        stream.write("]\n")


class SqliteStorage(EntityStorage):
    def __init__(self, path: str):
        super().__init__()
        self.path = path
        self.db: Optional[sqlite3.Connection] = None
        self.dbc: Optional[sqlite3.Cursor] = None
        self.saves = 0

    async def open_if_necessary(self):
        if self.db:
            return
        self.db = sqlite3.connect(self.path)
        self.dbc = self.db.cursor()
        self.dbc.execute(
            "CREATE TABLE IF NOT EXISTS entities (key TEXT NOT NULL PRIMARY KEY, gid INTEGER NOT NULL, serialized TEXT NOT NULL)"
        )
        self.db.commit()

        log.info("%s opened", self.path)

    async def load_query(self, query: str, args: Any):
        await self.open_if_necessary()
        assert self.db

        self.dbc = self.db.cursor()

        rows = {}
        for row in self.dbc.execute(query, args):
            rows[row[0]] = row[1]

        self.db.rollback()

        return [entity.Serialized(key, serialized) for key, serialized in rows.items()]

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

    async def update(self, updates: Dict[Keys, Optional[str]]):
        await self.open_if_necessary()
        assert self.db

        log.debug("applying %d updates", len(updates))

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
            return loaded
        return []

    async def load_by_key(self, key: str):
        loaded = await self.load_query(
            "SELECT key, serialized FROM entities WHERE key = ?", [key]
        )
        if len(loaded) == 1:
            return loaded
        return []

    def __repr__(self):
        return "Sqlite<%s>" % (self.path,)

    def __str__(self):
        return "Sqlite<%s>" % (self.path,)


class HttpStorage(EntityStorage):
    def __init__(self, url: str):
        super().__init__()
        self.url = url

    def session(self):
        return Client(
            transport=AIOHTTPTransport(url=self.url), fetch_schema_from_transport=True
        )

    async def number_of_entities(self):
        async with self.session() as session:
            query = gql("query { size }")
            response = await session.execute(query)
            return response["size"]

    async def update(self, updates: Dict[Keys, Optional[str]]):
        async with self.session() as session:
            query = gql(
                """
        mutation Update($entities: [EntityDiff!]) {
            update(entities: $entities) {
                affected
            }
        }
    """
            )
            entities = [
                {"key": key.key, "serialized": serialized}
                for key, serialized in updates.items()
                if serialized
            ]
            response = await session.execute(
                query, variable_values={"entities": entities}
            )
            return response["update"]["affected"]

    async def load_by_gid(self, gid: int):
        async with self.session() as session:
            query = gql(
                "query entityByGid($gid: Int!) { entitiesByGid(gid: $gid) { key serialized } }"
            )
            response = await session.execute(query, variable_values={"gid": gid})
            serialized_entities = response["entitiesByGid"]
            if len(serialized_entities) == 0:
                return []
            return [entity.Serialized(**row) for row in serialized_entities]

    async def load_by_key(self, key: str):
        async with self.session() as session:
            query = gql(
                "query entityByKey($key: Key!) { entitiesByKey(key: $key) { key serialized }}"
            )
            response = await session.execute(query, variable_values={"key": key})
            serialized_entities = response["entitiesByKey"]
            if len(serialized_entities) == 0:
                return []
            return [entity.Serialized(**row) for row in serialized_entities]

    def __repr__(self):
        return "Http<%s>" % (self.url,)

    def __str__(self):
        return "Http<%s>" % (self.url,)
