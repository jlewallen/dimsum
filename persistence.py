import logging
import sqlite3
import json
import props
import game


class SqlitePersistence:
    async def open(self, path: str):
        self.db = sqlite3.connect(path)
        self.dbc = self.db.cursor()
        self.dbc.execute(
            "CREATE TABLE IF NOT EXISTS entities (key TEXT NOT NULL PRIMARY KEY, klass TEXT NOT NULL, owner TEXT NOT NULL, properties TEXT NOT NULL)"
        )
        self.db.commit()

    async def save(self, world):
        self.dbc = self.db.cursor()

        for key in world.entities.keys():
            entity = world.entities[key]
            props = json.dumps(entity.saved())
            klass = entity.__class__.__name__
            self.dbc.execute(
                "INSERT INTO entities (key, klass, owner, properties) VALUES (?, ?, ?, ?) ON CONFLICT(key) DO UPDATE SET owner = EXCLUDED.owner, klass = EXCLUDED.klass, properties = EXCLUDED.properties",
                [entity.key, klass, entity.owner.key, props],
            )

        self.db.commit()

    async def load(self, world):
        self.dbc = self.db.cursor()

        factories = {
            "Player": game.Player,
            "Item": game.Item,
            "Area": game.Area,
            "Recipe": game.Recipe,
        }

        rows = {}

        for row in self.dbc.execute(
            "SELECT key, klass, owner, properties FROM entities"
        ):
            rows[row[0]] = row

        keyed = {}

        def get_instance(key):
            if key == "world":
                return world
            if key in keyed:
                return keyed[key][0]
            row = rows[key]
            factory = factories[row[1]]
            owner = get_instance(row[2])
            instance = factory(key=row[0], owner=owner, details=props.Details())
            instance.key = key
            properties = json.loads(row[3])
            keyed[key] = [instance, properties]
            return instance

        for key in rows.keys():
            world.register(get_instance(key))

        for key in keyed.keys():
            instance, properties = keyed[key]
            instance.load(world, properties)

        self.db.commit()
