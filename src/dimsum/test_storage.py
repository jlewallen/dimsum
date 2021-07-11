import logging
import pytest

import domains
import scopes
import serializing
import storage
from model import *


log = logging.getLogger("dimsum")


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
