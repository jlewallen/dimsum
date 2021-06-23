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
    domain = domains.Domain(storage=store, empty=True)
    assert not await serializing.materialize(domain.registrar, store, key="world")

    await store.update(serializing.for_update([world.World()]))

    assert await serializing.materialize(domain.registrar, store, key="world")


@pytest.mark.asyncio
async def test_storage_materialize_reference():
    store = storage.InMemory()
    domain = domains.Domain(storage=store)

    with domain.session() as session:
        session.add_area(
            scopes.area(creator=domain.world, props=properties.Common("Area"))
        )

    await store.update(serializing.registrar(domain.registrar))

    domain.registrar.purge()

    assert domain.registrar.number == 0

    assert await serializing.materialize(domain.registrar, store, key="world")

    assert domain.registrar.number == 2
