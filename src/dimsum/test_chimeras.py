import sys
import logging
import pytest

import context

import model.crypto as crypto
import model.entity as entity
import model.properties as properties
import model.world as world
import model.domains as domains

import model.scopes.ownership as ownership

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
    domain = domains.Domain()
    universe = domain.world

    jacob = entity.Entity(
        creator=universe, props=properties.Common(name="Jacob"), scopes=[SimpleCore]
    )
    domain.registrar.register(jacob)

    toy = entity.Entity(
        creator=universe, props=properties.Common(name="Toy"), scopes=[SimpleCore]
    )
    domain.registrar.register(toy)

    with jacob.make(SimpleHolding) as holding:
        with jacob.make(SimpleCore) as core:
            pass
        holding.add_item(toy)

    db = persistence.SqliteDatabase()
    await db.open("test.sqlite3")
    await db.purge()
    await db.save(domain.registrar)

    empty = domains.Domain()
    await db.load_all(empty.registrar)

    assert len(empty.registrar.entities) == 3


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
    domain = domains.Domain()
    universe = domain.world

    person = make_person(creator=universe, props=properties.Common(name="Jacob"))
    domain.registrar.register(person)

    toy = make_thing(creator=universe, props=properties.Common(name="Toy"))
    domain.registrar.register(toy)

    db = persistence.SqliteDatabase()
    await db.open("test.sqlite3")
    await db.purge()
    await db.save(domain.registrar)

    empty = domains.Domain()
    await db.load_all(empty.registrar)

    assert len(empty.registrar.entities) == 3
