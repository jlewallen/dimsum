import sys
import logging
import pytest

import context
import properties
import crypto
import chimeras
import entity
import luaproxy
import messages
import handlers
import world
import serializing
import persistence

import test


log = logging.getLogger("dimsum")


class SimpleCore(chimeras.Spawned):
    def __init__(self, name: str = None, frozen=None, destroyed=None, **kwargs):
        super().__init__(**kwargs)
        self.name = name
        self.frozen = frozen
        self.destroyed = destroyed


class SimpleHolding(chimeras.Spawned):
    def __init__(self, holding=None, **kwargs):
        super().__init__(**kwargs)
        self.holding = holding if holding else []

    def add_item(self, entity: chimeras.Chimera):
        self.holding.append(entity)


@pytest.mark.asyncio
async def test_chimeric_entities_serialize(caplog):
    bus = messages.TextBus(handlers=[handlers.WhateverHandlers])
    universe = world.World(bus, luaproxy.context_factory)

    jacob = chimeras.Chimera(creator=universe, props=properties.Common(name="Jacob"))
    universe.register(jacob)

    toy = chimeras.Chimera(creator=universe, props=properties.Common(name="Toy"))
    universe.register(toy)

    with jacob.make(SimpleHolding) as holding:
        with jacob.make(SimpleCore) as core:
            pass
        holding.add_item(toy)

    db = persistence.SqliteDatabase()
    await db.open("test.sqlite3")
    await db.purge()
    await db.save(universe)

    empty = world.World(bus, context_factory=universe.context_factory)
    await db.load(empty)

    assert await db.number_of_entities() == 3
