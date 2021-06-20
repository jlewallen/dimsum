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
    assert not await serializing.materialize("world", domain.registrar, store)

    await store.update(serializing.for_update([world.World()]))

    assert await serializing.materialize("world", domain.registrar, store)


@pytest.mark.asyncio
async def test_storage_materialize_reference():
    store = storage.InMemory()
    domain = domains.Domain(storage=store)

    domain.add_area(scopes.area(creator=domain.world, props=properties.Common("Area")))

    await store.update(serializing.registrar(domain.registrar))

    domain.registrar.purge()

    assert domain.registrar.number == 0

    assert await serializing.materialize("world", domain.registrar, store)

    assert domain.registrar.number == 2
