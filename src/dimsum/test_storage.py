import pytest
import logging

import model.properties as properties
import model.domains as domains
import model.world as world
import model.scopes as scopes

import storage
import serializing

log = logging.getLogger("dimsum")


@pytest.mark.asyncio
async def test_storage_materialize_world():
    store = storage.InMemory()
    domain = domains.Domain(storage=store)
    with domain.session() as session:
        assert not await serializing.materialize(
            session.registrar, store, key=world.Key
        )

        await store.update(serializing.for_update([world.World()]))

        assert await serializing.materialize(
            registrar=session.registrar, store=store, key=world.Key
        )


@pytest.mark.asyncio
async def test_storage_materialize_reference():
    store = storage.InMemory()
    domain = domains.Domain(store=store)

    with domain.session() as session:
        await session.prepare()

        await session.add_area(
            scopes.area(creator=session.world, props=properties.Common("Area"))
        )

        await session.save()

    with domain.session() as session:
        assert session.registrar.number_of_entities() == 0

        assert await serializing.materialize(
            registrar=session.registrar, store=store, key=world.Key
        )

        assert session.registrar.number_of_entities() == 2
