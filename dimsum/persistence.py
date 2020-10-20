from typing import Dict

import logging
import sqlite3
import json

import props
import entity
import crypto
import game
import world
import serializing

log = logging.getLogger("dimsum")


class SqliteDatabase:
    async def open(self, path: str):
        self.db = sqlite3.connect(path)
        self.dbc = self.db.cursor()
        self.dbc.execute(
            "CREATE TABLE IF NOT EXISTS entities (key TEXT NOT NULL PRIMARY KEY, klass TEXT NOT NULL, identity TEXT NOT NULL, serialized TEXT NOT NULL)"
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
        klass = entity.__class__.__name__
        props = serializing.serialize(entity, secure=True, indent=4)
        identity_field = {
            "private": entity.identity.private,
            "signature": entity.identity.signature,
        }
        log.info("saving %s %s %s", entity.key, entity, entity.__class__.__name__)
        self.dbc.execute(
            "INSERT INTO entities (key, klass, identity, serialized) VALUES (?, ?, ?, ?) ON CONFLICT(key) DO UPDATE SET klass = EXCLUDED.klass, serialized = EXCLUDED.serialized",
            [
                entity.key,
                klass,
                json.dumps(identity_field),
                props,
            ],
        )

    async def save(self, world: world.World):
        self.dbc = self.db.cursor()

        for key, entity in world.garbage.items():
            await self.destroy(entity)

        for key, entity in world.entities.items():
            try:
                if entity.destroyed:
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

        self.db.commit()

    async def load(self, world: world.World):
        self.dbc = self.db.cursor()

        rows = {}
        for row in self.dbc.execute(
            "SELECT key, klass, identity, serialized FROM entities"
        ):
            rows[row[0]] = row

        refs: Dict[str, Dict] = {}

        def reference(key):
            if key is None:
                return world
            if key in refs:
                return refs[key]
            refs[key] = {"key": key}
            return refs[key]

        cached: Dict[str, entity.Entity] = {}
        for key in rows.keys():
            log.info("restoring: key=%s %s", key, row[1])
            e = serializing.deserialize(row[3], reference)
            assert isinstance(e, entity.Entity)
            world.register(e)
            cached[key] = e

        for key, baby_entity in refs.items():
            log.info("resolve: %s", key)
            baby_entity.update(cached[key].__dict__)

        self.db.commit()
