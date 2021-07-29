import dataclasses
import sqlite3
import json
import copy
import shutil
import datetime
import os.path
from typing import Any, Dict, List, Optional, TextIO

from loggers import get_logger
from model import Entity, CompiledJson, Serialized

from .core import EntityStorage

log = get_logger("dimsum.storage")


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


class SqliteStorage(EntityStorage):
    def __init__(self, path: str, read_only=False):
        super().__init__()
        self.path = path
        self.read_only = read_only
        self.db: Optional[sqlite3.Connection] = None
        self.dbc: Optional[sqlite3.Cursor] = None
        self.saves = 0
        self.frozen = False

    async def open_if_necessary(self):
        if self.db:
            return
        if not self.read_only:
            if os.path.isfile(self.path):
                now = datetime.datetime.now()
                suffix = now.strftime("%Y%m%d_%H%M%S")
                inside_dir = os.path.dirname(self.path)
                file_name = os.path.basename(self.path)
                backups_dir = os.path.join(inside_dir, ".backups")
                os.makedirs(backups_dir, exist_ok=True)
                backup_file = os.path.join(backups_dir, f"{file_name}.{suffix}")
                shutil.copyfile(self.path, backup_file)
        if self.path == ":memory:" or not self.read_only:
            self.db = sqlite3.connect(self.path)
        else:
            self.db = sqlite3.connect(f"file:{self.path}?mode=ro", uri=True)
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
        try:
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
        finally:
            self.db.rollback()

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

    async def load_all_keys(self) -> List[str]:
        await self.open_if_necessary()
        assert self.db

        self.dbc = self.db.cursor()
        rows = self.dbc.execute("SELECT key FROM entities").fetchall()
        return [row[0] for row in rows]

    def freeze(self):
        self.frozen = True

    def __repr__(self):
        return "Sqlite<%s>" % (self.path,)

    def __str__(self):
        return "Sqlite<%s>" % (self.path,)
