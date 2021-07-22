import logging
import shortuuid
import sqlite3
import pytest

import domains
import scopes
import serializing
import storage
from loggers import get_logger
from model import *


log = get_logger("dimsum")


@pytest.mark.asyncio
async def test_storage_materialize_world():
    store = storage.SqliteStorage(":memory:")
    domain = domains.Domain(storage=store)
    with domain.session() as session:
        before = await serializing.materialize(session.registrar, store, key=WorldKey)
        assert before.empty()

        await store.update(serializing.for_update([World()]))
        after = await serializing.materialize(
            registrar=session.registrar, store=store, key=WorldKey
        )
        assert after.one()


@pytest.mark.asyncio
async def test_storage_materialize_reference():
    store = storage.SqliteStorage(":memory:")
    domain = domains.Domain(store=store)

    with domain.session() as session:
        w = await session.prepare()
        await session.add_area(scopes.area(creator=w, props=Common("Area")))
        await session.save()

    with domain.session() as session:
        assert session.registrar.number_of_entities() == 0
        await session.prepare()
        assert await serializing.materialize(
            registrar=session.registrar, store=store, key=WorldKey
        )
        assert session.registrar.number_of_entities() == 1


@pytest.mark.asyncio
async def test_storage_only_save_modified_super_simple():
    store = storage.SqliteStorage(":memory:")
    domain = domains.Domain(store=store)

    with domain.session() as session:
        w = await session.prepare()
        await session.add_area(scopes.area(creator=w, props=Common("Area")))
        await session.save()

    with domain.session() as session:
        assert session.registrar.number_of_entities() == 0
        await session.prepare()
        assert await serializing.materialize(
            registrar=session.registrar, store=store, key=WorldKey
        )
        assert session.registrar.number_of_entities() == 1

        store.freeze()

        await session.save()


@pytest.mark.asyncio
async def test_storage_update_fails_and_rolls_back(caplog):
    store = storage.SqliteStorage(":memory:")
    domain = domains.Domain(store=store)

    area_1_key = shortuuid.uuid()
    area_2_key = shortuuid.uuid()
    with domain.session() as session:
        world = await session.prepare()
        await session.add_area(
            scopes.area(key=area_1_key, creator=world, props=Common("Area One"))
        )
        await session.add_area(
            scopes.area(key=area_2_key, creator=world, props=Common("Area Two"))
        )
        await session.save()

    with pytest.raises(sqlite3.IntegrityError):
        with caplog.at_level(logging.CRITICAL):
            with domain.session() as session:
                world = await session.prepare()
                area_1 = await session.materialize(key=area_1_key)
                assert area_1
                area_2 = await session.materialize(key=area_2_key)
                assert area_2
                area_1.props.name = "Area Three"
                area_2.version.i = 0
                area_1.touch()
                area_2.touch()
                await session.save()

    with domain.session() as session:
        world = await session.prepare()
        area_2 = await session.materialize(key=area_2_key)
        assert area_2
        area_2.touch()
        await session.save()

    with domain.session() as session:
        world = await session.prepare()
        area_1 = await session.materialize(key=area_1_key)
        assert area_1
        area_1.touch()
        await session.save()
