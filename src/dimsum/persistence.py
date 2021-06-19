from typing import Dict, TextIO, Any

import logging
import sqlite3
import json

import model.entity as entity
import model.world as world

import serializing

log = logging.getLogger("dimsum")


class SqliteDatabase:
    async def open(self, path: str):
        self.db = sqlite3.connect(path)
        self.dbc = self.db.cursor()
        self.dbc.execute(
            "CREATE TABLE IF NOT EXISTS entities (key TEXT NOT NULL PRIMARY KEY, gid INTEGER NOT NULL, klass TEXT NOT NULL, identity TEXT NOT NULL, serialized TEXT NOT NULL)"
        )
        self.db.commit()

    async def number_of_entities(self):
        self.dbc = self.db.cursor()
        return self.dbc.execute("SELECT COUNT(*) FROM entities").fetchone()[0]

    async def purge(self):
        self.dbc = self.db.cursor()
        self.dbc.execute("DELETE FROM entities")
        self.db.commit()

    async def destroy(self, entity: entity.Entity):
        klass = entity.__class__.__name__
        log.info("destroying %s %s %s", entity.key, entity, entity.__class__.__name__)
        self.dbc.execute(
            "DELETE FROM entities WHERE key = ?",
            [
                entity.key,
            ],
        )

    async def update(self, entity: entity.Entity):
        gid = entity.props.gid
        klass = entity.__class__.__name__
        serialized = serializing.serialize(entity, secure=True)
        identity_field = {
            "private": entity.identity.private,
            "signature": entity.identity.signature,
        }
        # log.debug("saving %s %s %s", entity.key, entity, entity.__class__.__name__)
        self.dbc.execute(
            "INSERT INTO entities (key, gid, klass, identity, serialized) VALUES (?, ?, ?, ?, ?) ON CONFLICT(key) DO UPDATE SET klass = EXCLUDED.klass, gid = EXCLUDED.gid, serialized = EXCLUDED.serialized",
            [
                entity.key,
                gid,
                klass,
                json.dumps(identity_field),
                serialized,
            ],
        )

    async def save(self, world: world.World):
        self.dbc = self.db.cursor()

        for key, entity in world.garbage.items():
            await self.destroy(entity)

        log.info("deleted %d entities in garbage", len(world.garbage.keys()))

        for key, entity in world.entities.items():
            try:
                if entity.props.destroyed:
                    await self.destroy(entity)
                else:
                    await self.update(entity)
            except:
                log.error(
                    "error:saving %s = %s",
                    key,
                    entity,
                    exc_info=True,
                )
                raise

        log.info("saved %d entities", len(world.entities.keys()))

        self.db.commit()

    async def load_all(self, world: world.World):
        return await self.load_query(world, "SELECT key, serialized FROM entities", [])

    async def load_entity_by_gid(self, world: world.World, gid: int):
        loaded = await self.load_query(
            world, "SELECT key, serialized FROM entities WHERE gid = ?", [gid]
        )
        if len(loaded) == 1:
            return loaded[0]
        return None

    async def load_entity_by_key(self, world: world.World, key: str):
        loaded = await self.load_query(
            world, "SELECT key, serialized FROM entities WHERE key = ?", [key]
        )
        if len(loaded) == 1:
            return loaded[0]
        return None

    async def load_query(self, world: world.World, query: str, args: Any):
        self.dbc = self.db.cursor()

        rows = {}
        for row in self.dbc.execute(query, args):
            rows[row[0]] = row[1]

        self.db.rollback()

        return serializing.restore(world, rows)

    async def write(self, stream: TextIO):
        stream.write("[\n")
        prefix = ""
        for row in self.dbc.execute("SELECT key, serialized FROM entities"):
            stream.write(prefix)
            stream.write(row[1])
            prefix = ","
        stream.write("]\n")
