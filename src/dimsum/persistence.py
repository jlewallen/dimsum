from typing import Dict

import logging
import sqlite3
import json

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
        props = serializing.serialize(entity, secure=True)
        identity_field = {
            "private": entity.identity.private,
            "signature": entity.identity.signature,
        }
        # log.debug("saving %s %s %s", entity.key, entity, entity.__class__.__name__)
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

    async def load(self, world: world.World):
        self.dbc = self.db.cursor()

        rows = {}
        for row in self.dbc.execute("SELECT key, serialized FROM entities"):
            rows[row[0]] = row[1]

        entities = serializing.restore(world, rows)

        self.db.commit()

    async def write(self, fn: str):
        with open(fn, "w") as file:
            file.write("[\n")
            prefix = ""
            for row in self.dbc.execute("SELECT key, serialized FROM entities"):
                file.write(prefix)
                file.write(row[1])
                prefix = ","
            file.write("]\n")
