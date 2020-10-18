from typing import Dict

import logging
import sqlite3
import json

import props
import entity
import crypto
import game
import serializing


class SqlitePersistence:
    async def open(self, path: str):
        self.db = sqlite3.connect(path)
        self.dbc = self.db.cursor()
        self.dbc.execute(
            "CREATE TABLE IF NOT EXISTS entities (key TEXT NOT NULL PRIMARY KEY, klass TEXT NOT NULL, identity TEXT NOT NULL, serialized TEXT NOT NULL)"
        )
        self.db.commit()

    async def save(self, world: game.World):
        self.dbc = self.db.cursor()

        for key in world.entities.keys():
            entity = world.entities[key]
            klass = entity.__class__.__name__
            props = serializing.serialize(entity)
            identity_field = {
                "private": entity.identity.private,
                "signature": entity.identity.signature,
            }

            try:
                logging.info("saving %s %s %s", key, entity, entity.__class__.__name__)
                self.dbc.execute(
                    "INSERT INTO entities (key, klass, identity, serialized) VALUES (?, ?, ?, ?) ON CONFLICT(key) DO UPDATE SET klass = EXCLUDED.klass, serialized = EXCLUDED.serialized",
                    [
                        entity.key,
                        klass,
                        json.dumps(identity_field),
                        props,
                    ],
                )
            except:
                logging.error(
                    "error:saving %s %s %s",
                    key,
                    entity,
                    entity.__class__.__name__,
                    exc_info=True,
                )
                raise

        self.db.commit()

    async def load(self, world: game.World):
        self.dbc = self.db.cursor()

        rows = {}
        for row in self.dbc.execute(
            "SELECT key, klass, identity, serialized FROM entities"
        ):
            rows[row[0]] = row

        cached: Dict[str, entity.Entity] = {}

        def lookup(key: str):
            if key is None or key == "world":
                return world
            if key in cached:
                return cached[key]
            row = rows[key]
            logging.info("restoring: key=%s %s", key, row[1])
            instance = serializing.deserialize(row[3], lookup)
            if not isinstance(instance, entity.Entity):
                logging.error("error deserializing: %s", row[3])
                raise Exception("expected entity")
            cached[key] = instance
            return instance

        for key in rows.keys():
            instance = lookup(key)
            logging.info("registering: %s %s", type(instance), instance)
            world.register(instance)

        self.db.commit()
