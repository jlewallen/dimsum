import logging

import model.domains as domains
import model.properties as properties
import model.scopes as scopes
import model.world as world
import pytest
import serializing
import storage

log = logging.getLogger("dimsum")


@pytest.mark.asyncio
async def test_storage_materialize_world():
    store = storage.SqliteStorage(":memory:")
    domain = domains.Domain(storage=store)
    with domain.session() as session:
        before = await serializing.materialize(session.registrar, store, key=world.Key)
        assert before.empty()

        await store.update(serializing.for_update([world.World()]))
        after = await serializing.materialize(
            registrar=session.registrar, store=store, key=world.Key
        )
        assert after.one()


@pytest.mark.asyncio
async def test_storage_materialize_reference():
    store = storage.SqliteStorage(":memory:")
    domain = domains.Domain(store=store)

    with domain.session() as session:
        w = await session.prepare()
        await session.add_area(scopes.area(creator=w, props=properties.Common("Area")))
        await session.save()

    with domain.session() as session:
        assert session.registrar.number_of_entities() == 0
        await session.prepare()
        assert await serializing.materialize(
            registrar=session.registrar, store=store, key=world.Key
        )
        assert session.registrar.number_of_entities() == 2


@pytest.mark.asyncio
async def test_storage_only_save_modified_super_simple():
    store = storage.SqliteStorage(":memory:")
    domain = domains.Domain(store=store)

    with domain.session() as session:
        w = await session.prepare()
        await session.add_area(scopes.area(creator=w, props=properties.Common("Area")))
        await session.save()

    with domain.session() as session:
        assert session.registrar.number_of_entities() == 0
        await session.prepare()
        assert await serializing.materialize(
            registrar=session.registrar, store=store, key=world.Key
        )
        assert session.registrar.number_of_entities() == 2

        store.freeze()

        await session.save()
