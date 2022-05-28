import dataclasses
import json
import copy
import shutil
import datetime
import os.path
import aiosqlite
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


def backup(now: datetime.datetime, path: str) -> Optional[str]:
    if not os.path.isfile(path):
        return None
    suffix = now.strftime("%Y%m%d_%H%M%S")
    inside_dir = os.path.dirname(path)
    file_name = os.path.basename(path)
    backups_dir = os.path.join(inside_dir, ".backups")
    backup_file = os.path.join(backups_dir, f"{file_name}.{suffix}")
    if os.path.isfile(backup_file):
        return None
    os.makedirs(backups_dir, exist_ok=True)
    shutil.copyfile(path, backup_file)
    return backup_file


class SqliteStorage(EntityStorage):
    def __init__(self, path: str, read_only=False):
        super().__init__()
        self.path = path
        self.read_only = read_only
        self.db: Optional[aiosqlite.Connection] = None
        self.saves = 0
        self.frozen = False
        self.last_backup: Optional[str] = None

    async def open_if_necessary(self):
        if self.db:
            return

        await self.backup(datetime.datetime.now())

        if self.path == ":memory:" or not self.read_only:
            log.debug(f"db:opening {self.path}")
            self.db = await aiosqlite.connect(self.path)
        else:
            log.debug(f"db:opening {self.path} read-only")
            self.db = await aiosqlite.connect(f"file:{self.path}?mode=ro", uri=True)

        dbc = await self.db.execute(
            "CREATE TABLE IF NOT EXISTS entities (key TEXT NOT NULL PRIMARY KEY, version INTEGER NOT NULL, gid INTEGER, serialized TEXT NOT NULL)"
        )
        await dbc.close()
        await self.db.commit()

        log.info("%s opened", self.path)

    async def load_query(self, query: str, args: Any) -> List[Serialized]:
        await self.open_if_necessary()
        assert self.db

        rows = {}
        dbc = await self.db.execute(query, args)
        for row in await dbc.fetchall():
            rows[row[0]] = row[1]

        await dbc.close()
        await self.db.commit()

        return [Serialized(key, serialized) for key, serialized in rows.items()]

    async def write(self, stream: TextIO):
        await self.open_if_necessary()
        assert self.db

        dbc = await self.db.execute("SELECT key, serialized FROM entities")
        stream.write("[\n")
        prefix = ""
        for row in await dbc.fetchall():
            stream.write(prefix)
            stream.write(row[1])
            prefix = ","
        stream.write("]\n")

        await dbc.close()
        await self.db.commit()

    async def number_of_entities(self):
        await self.open_if_necessary()
        assert self.db

        dbc = await self.db.execute("SELECT COUNT(*) FROM entities")
        row = await dbc.fetchone()
        await dbc.close()
        await self.db.commit()
        assert row
        return row[0]

    async def purge(self):
        await self.open_if_necessary()
        assert self.db

        dbc = await self.db.execute("DELETE FROM entities")
        await dbc.close()
        await self.db.commit()

    async def _delete_row(self, fields: StorageFields):
        assert self.db
        log.debug(
            "deleting %s version=%d original=%d",
            fields.key,
            fields.version,
            fields.original,
        )
        dbc = await self.db.execute(
            "DELETE FROM entities WHERE key = ? AND version = ?",
            [fields.key, fields.original],
        )
        await dbc.close()

    async def _update_row(self, fields: StorageFields):
        assert self.db
        log.debug(
            "updating %s version=%d original=%d",
            fields.key,
            fields.version,
            fields.original,
        )
        try:
            dbc = await self.db.execute(
                "UPDATE entities SET version = ?, gid = ?, serialized = ? WHERE key = ? AND version = ?",
                [
                    fields.version,
                    fields.gid,
                    fields.saved.text,
                    fields.key,
                    fields.original,
                ],
            )
            await dbc.close()
            if dbc.rowcount != 1:
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

    async def _insert_row(self, fields: StorageFields):
        assert self.db
        log.debug(
            "inserting %s version=%d original=%d",
            fields.key,
            fields.version,
            fields.original,
        )
        try:
            dbc = await self.db.execute(
                "INSERT INTO entities (key, gid, version, serialized) VALUES (?, ?, ?, ?) ",
                [
                    fields.key,
                    fields.gid,
                    fields.version,
                    fields.saved.text,
                ],
            )
            await dbc.close()
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

        log.info("applying %d updates", len(updates))

        updating = {key: StorageFields.parse(update) for key, update in updates.items()}

        try:
            for key, fields in updating.items():
                assert not self.frozen
                if fields.destroyed:
                    await self._delete_row(fields)
                else:
                    if fields.original == 0:
                        await self._insert_row(fields)
                    else:
                        await self._update_row(fields)

            await self.db.commit()

            return {key: f.saved for key, f in updating.items() if not f.destroyed}
        finally:
            if self.db:
                await self.db.rollback()

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

        dbc = await self.db.execute("SELECT key FROM entities")
        rows = await dbc.fetchall()
        keys = [row[0] for row in rows]
        await dbc.close()
        await self.db.commit()
        return keys

    def freeze(self):
        self.frozen = True

    async def close(self):
        if self.db:
            await self.db.close()
            self.db = None

    async def backup(self, now: datetime.datetime) -> Optional[List[str]]:
        if not self.read_only:
            file = backup(now, self.path)
            if file:
                return [file]
        return []

    def __str__(self):
        return f"Sqlite<{self.path}>"

    def __repr__(self):
        return str(self)
