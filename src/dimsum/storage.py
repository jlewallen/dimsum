import dataclasses
import json
import copy
import logging
import sqlite3
from typing import Any, Dict, List, Optional, TextIO
from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport

from model import Entity, CompiledJson, Serialized

log = logging.getLogger("dimsum.storage")


@dataclasses.dataclass
class StorageFields:
    key: str
    gid: int
    version: int
    original: int
    destroyed: bool
    saving: CompiledJson
    saved: CompiledJson

    @staticmethod
    def parse(cj: CompiledJson):
        try:
            parsed = copy.copy(cj.compiled)
            parsed["version"] = copy.copy(parsed["version"])
            key = parsed["key"]
            gid = parsed["props"]["map"]["gid"]["value"]
            destroyed = parsed["props"]["map"]["destroyed"]["value"] is not None
            original = parsed["version"]["i"]
            version = original + 1
            parsed["version"]["i"] = version
            saved = CompiledJson(json.dumps(parsed), parsed)
            return StorageFields(key, gid, version, original, destroyed, cj, saved)
        except KeyError:
            raise Exception("malformed entity: {0}".format(cj.text))


class EntityStorage:
    async def number_of_entities(self) -> int:
        raise NotImplementedError

    async def update(self, updates: Dict[str, CompiledJson]) -> Dict[str, CompiledJson]:
        raise NotImplementedError

    async def load_by_gid(self, gid: int) -> List[Serialized]:
        raise NotImplementedError

    async def load_by_key(self, key: str) -> List[Serialized]:
        raise NotImplementedError


class All(EntityStorage):
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

    def __str__(self):
        return "Prioritized<{0}>".format(self.children)


class Separated(EntityStorage):
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

    def __str__(self):
        return "Separated<read={0}, write={1}>".format(self.read, self.write)


class SqliteStorage(EntityStorage):
    def __init__(self, path: str):
        super().__init__()
        self.path = path
        self.db: Optional[sqlite3.Connection] = None
        self.dbc: Optional[sqlite3.Cursor] = None
        self.saves = 0
        self.frozen = False

    async def open_if_necessary(self):
        if self.db:
            return
        self.db = sqlite3.connect(self.path)
        self.dbc = self.db.cursor()
        self.dbc.execute(
            "CREATE TABLE IF NOT EXISTS entities (key TEXT NOT NULL PRIMARY KEY, version INTEGER NOT NULL, gid INTEGER, serialized TEXT NOT NULL)"
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

        return [Serialized(key, serialized) for key, serialized in rows.items()]

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

    def _delete_row(self, fields: StorageFields):
        assert self.dbc
        log.debug(
            "deleting %s version=%d original=%d",
            fields.key,
            fields.version,
            fields.original,
        )
        self.dbc.execute(
            "DELETE FROM entities WHERE key = ? AND version = ?",
            [fields.key, fields.original],
        )

    def _update_row(self, fields: StorageFields):
        assert self.dbc
        log.debug(
            "updating %s version=%d original=%d",
            fields.key,
            fields.version,
            fields.original,
        )
        try:
            rv = self.dbc.execute(
                "UPDATE entities SET version = ?, gid = ?, serialized = ? WHERE key = ? AND version = ?",
                [
                    fields.version,
                    fields.gid,
                    fields.saved.text,
                    fields.key,
                    fields.original,
                ],
            )
            if rv.rowcount != 1:
                raise Exception("update failed")
        except:
            log.exception("UPDATE error", exc_info=True)
            log.error(
                "serialized key=%s original=%d version=%d",
                fields.key,
                fields.original,
                fields.version,
            )
            log.error("saving=%s", fields.saving)
            log.error("saved=%s", fields.saved)
            raise

    def _insert_row(self, fields: StorageFields):
        assert self.dbc
        log.debug(
            "inserting %s version=%d original=%d",
            fields.key,
            fields.version,
            fields.original,
        )
        try:
            self.dbc.execute(
                "INSERT INTO entities (key, gid, version, serialized) VALUES (?, ?, ?, ?) ",
                [
                    fields.key,
                    fields.gid,
                    fields.version,
                    fields.saved.text,
                ],
            )
        except:
            log.exception("INSERT error", exc_info=True)
            log.error(
                "serialized key=%s original=%d version=%d",
                fields.key,
                fields.original,
                fields.version,
            )
            log.error("saving=%s", fields.saving)
            log.error("saved=%s", fields.saved)
            raise

    async def update(self, updates: Dict[str, CompiledJson]) -> Dict[str, CompiledJson]:
        await self.open_if_necessary()
        assert self.db

        log.debug("applying %d updates", len(updates))

        updating = {key: StorageFields.parse(update) for key, update in updates.items()}

        self.dbc = self.db.cursor()
        for key, fields in updating.items():
            assert not self.frozen
            if fields.destroyed:
                self._delete_row(fields)
            else:
                if fields.original == 0:
                    self._insert_row(fields)
                else:
                    self._update_row(fields)

        self.db.commit()

        return {key: f.saved for key, f in updating.items() if not f.destroyed}

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

    def freeze(self):
        self.frozen = True

    def __repr__(self):
        return "Sqlite<%s>" % (self.path,)

    def __str__(self):
        return "Sqlite<%s>" % (self.path,)


class HttpStorage(EntityStorage):
    def __init__(self, url: str, token: Optional[str] = None):
        super().__init__()
        self.url = url
        self.token = token

    def _get_headers(self):
        if self.token:
            return {"Authorization": "Bearer %s" % (self.token,)}
        return {}

    def session(self):
        return Client(
            transport=AIOHTTPTransport(url=self.url, headers=self._get_headers()),
            fetch_schema_from_transport=True,
        )

    async def number_of_entities(self):
        async with self.session() as session:
            query = gql("query { size }")
            response = await session.execute(query)
            return response["size"]

    async def update(self, updates: Dict[str, CompiledJson]) -> Dict[str, CompiledJson]:
        async with self.session() as session:
            query = gql(
                """
        mutation Update($entities: [EntityDiff!]) {
            update(entities: $entities) {
                affected { key serialized }
            }
        }
    """
            )
            entities = [
                {"key": key, "serialized": update.text}
                for key, update in updates.items()
            ]
            response = await session.execute(
                query, variable_values={"entities": entities}
            )

            affected = response["update"]["affected"]
            return {row["key"]: row["serialized"] for row in affected}

    async def load_by_gid(self, gid: int):
        async with self.session() as session:
            query = gql(
                "query entityByGid($gid: Int!) { entitiesByGid(gid: $gid) { key serialized } }"
            )
            response = await session.execute(query, variable_values={"gid": gid})
            serialized_entities = response["entitiesByGid"]
            if len(serialized_entities) == 0:
                return []
            return [Serialized(**row) for row in serialized_entities]

    async def load_by_key(self, key: str):
        async with self.session() as session:
            query = gql(
                "query entityByKey($key: Key!) { entitiesByKey(key: $key) { key serialized }}"
            )
            response = await session.execute(query, variable_values={"key": key})
            serialized_entities = response["entitiesByKey"]
            if len(serialized_entities) == 0:
                return []
            return [Serialized(**row) for row in serialized_entities]

    def __repr__(self):
        return "Http<%s>" % (self.url,)

    def __str__(self):
        return "Http<%s>" % (self.url,)
