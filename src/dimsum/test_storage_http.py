from typing import Dict, List, Optional
from multiprocessing import Process

import json
import logging
import contextlib
import time
import asyncio
import shortuuid
import freezegun
import pytest

from gql import gql, Client
from gql.transport.aiohttp import AIOHTTPTransport

import uvicorn

import storage
import serializing
import dimsum
import test

import model.properties as properties
import model.entity as entity
import model.world as world

log = logging.getLogger("dimsum")


@pytest.fixture(scope="function")
def silence_aihttp(caplog):
    caplog.set_level(logging.CRITICAL, "gql.transport.aiohttp")
    yield


def session(url: str):
    return Client(transport=AIOHTTPTransport(url=url), fetch_schema_from_transport=True)


async def initialize(url: str):
    async with session(url) as s:
        query = gql("mutation { makeSample { affected { key } } }")
        await s.execute(query)


@pytest.fixture(scope="session")
def server():
    log.info("started server")
    proc = Process(
        target=uvicorn.run,
        args=(dimsum.app,),
        kwargs={
            "host": "127.0.0.1",
            "port": 45600,
            "log_level": "info",
            "factory": True,
        },
        daemon=True,
    )
    proc.start()
    time.sleep(0.5)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(initialize("http://127.0.0.1:45600"))

    yield

    proc.kill()


@pytest.mark.asyncio
async def test_storage_http_number_of_entities(server, silence_aihttp):
    store = storage.HttpStorage("http://127.0.0.1:45600")
    size = await store.number_of_entities()
    assert size == 60


@pytest.mark.asyncio
async def test_storage_load_by_key(server, silence_aihttp):
    store = storage.HttpStorage("http://127.0.0.1:45600")
    serialized = await store.load_by_key("world")
    assert [json.loads(s.serialized) for s in serialized]


@pytest.mark.asyncio
async def test_storage_load_by_gid(server, silence_aihttp):
    store = storage.HttpStorage("http://127.0.0.1:45600")
    serialized = await store.load_by_gid(0)
    assert [json.loads(s.serialized) for s in serialized]


@pytest.mark.asyncio
async def test_storage_update_nothing(server, silence_aihttp):
    store = storage.HttpStorage("http://127.0.0.1:45600")
    serialized = await store.update({})
    assert serialized == {}


@pytest.fixture(scope="session")
def deterministic():
    with test.Deterministic():
        yield


@pytest.mark.asyncio
@freezegun.freeze_time("2019-09-25")
async def test_storage_update_one_entity(
    snapshot, server, silence_aihttp, deterministic
):
    w = entity.Entity(props=properties.Common(name="Fake Entity"))
    serialized = serializing.serialize(w)
    assert serialized

    store = storage.HttpStorage("http://127.0.0.1:45600")
    key = shortuuid.uuid(name="example-1")

    updated = await store.update({entity.Keys(key): entity.EntityUpdate(serialized)})
    snapshot.assert_match(test.pretty_json(updated), "before.json")

    w.version.increase()
    serialized = serializing.serialize(w)
    assert serialized

    updated = await store.update({entity.Keys(key): entity.EntityUpdate(serialized)})
    snapshot.assert_match(test.pretty_json(updated), "after.json")


@pytest.mark.asyncio
@freezegun.freeze_time("2019-09-25")
async def test_storage_delete_one_entity(
    snapshot, server, silence_aihttp, deterministic
):
    w = entity.Entity(props=properties.Common(name="Fake Entity"))
    serialized = serializing.serialize(w)
    assert serialized

    store = storage.HttpStorage("http://127.0.0.1:45600")
    key = shortuuid.uuid(name="example-2")
    updated = await store.update({entity.Keys(key): entity.EntityUpdate(serialized)})
    snapshot.assert_match(test.pretty_json(updated), "before.json")

    w.version.increase()
    w.destroy()
    serialized = serializing.serialize(w)
    assert serialized

    updated = await store.update({entity.Keys(key): entity.EntityUpdate(serialized)})
    snapshot.assert_match(test.pretty_json(updated), "after.json")
