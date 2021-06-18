import sys
import logging
import pytest

import context

import model.properties as properties
import model.crypto as crypto
import model.entity as entity
import model.world as world
import model.ownership as ownership

import handlers
import messages
import luaproxy
import serializing
import persistence

import test


log = logging.getLogger("dimsum")


class SimpleCore(entity.Scope):
    def __init__(self, name: str = None, **kwargs):
        super().__init__(**kwargs)
        self.name = name


class SimpleHolding(entity.Scope):
    def __init__(self, holding=None, **kwargs):
        super().__init__(**kwargs)
        self.holding = holding if holding else []

    def add_item(self, entity: entity.Entity):
        self.holding.append(entity)


@pytest.mark.asyncio
async def test_chimeric_entities_serialize(caplog):
    bus = messages.TextBus(handlers=[handlers.WhateverHandlers])
    universe = world.World(bus, luaproxy.context_factory)

    jacob = entity.Entity(
        creator=universe, props=properties.Common(name="Jacob"), scopes=[SimpleCore]
    )
    universe.register(jacob)

    toy = entity.Entity(
        creator=universe, props=properties.Common(name="Toy"), scopes=[SimpleCore]
    )
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


def make_person(
    props: properties.Common = None, creator: entity.Entity = None, **kwargs
):
    person = entity.Entity(props=props, creator=creator, scopes=[SimpleCore], **kwargs)

    assert props

    with person.make(SimpleCore) as core:
        core.name = props.name

    with person.make(SimpleHolding) as holding:
        pass

    return person


def make_thing(
    props: properties.Common = None, creator: entity.Entity = None, **kwargs
):
    thing = entity.Entity(
        props=props, creator=creator, scopes=[ownership.Ownership], **kwargs
    )

    assert props

    with thing.make(ownership.Ownership) as change:
        change.owner = creator

    with thing.make(SimpleCore) as core:
        core.name = props.name

    with thing.make(SimpleHolding) as holding:
        pass

    return thing


@pytest.mark.asyncio
async def test_specialization_classes(caplog):
    bus = messages.TextBus(handlers=[handlers.WhateverHandlers])
    universe = world.World(bus, luaproxy.context_factory)

    person = make_person(creator=universe, props=properties.Common(name="Jacob"))
    universe.register(person)

    toy = make_thing(creator=universe, props=properties.Common(name="Toy"))
    universe.register(toy)

    db = persistence.SqliteDatabase()
    await db.open("test.sqlite3")
    await db.purge()
    await db.save(universe)

    empty = world.World(bus, context_factory=universe.context_factory)
    await db.load(empty)

    assert await db.number_of_entities() == 3
