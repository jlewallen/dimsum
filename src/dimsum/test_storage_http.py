from typing import Dict, List, Optional
from multiprocessing import Process

import json
import logging
import contextlib
import time
import asyncio
import shortuuid
import pytest

from gql import gql, Client
from gql.transport.aiohttp import AIOHTTPTransport

import uvicorn

import storage
import serializing
import dimsum

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
        query = gql("mutation { makeSample { affected } }")
        await s.execute(query)


@pytest.fixture(scope="session")
def server():
    log.info("started server")
    proc = Process(
        target=uvicorn.run,
        args=(dimsum.app,),
        kwargs={"host": "127.0.0.1", "port": 45600, "log_level": "info"},
        daemon=True,
    )
    proc.start()
    time.sleep(0.1)

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
    assert serialized == 0


@pytest.mark.asyncio
async def test_storage_update_one_entity(server, silence_aihttp):
    serialized = serializing.serialize(world.World())
    store = storage.HttpStorage("http://127.0.0.1:45600")
    serialized = await store.update({storage.Keys("world", 0): serialized})
    assert serialized == 1


@pytest.mark.asyncio
async def test_storage_delete_one_entity(server, silence_aihttp):
    serialized = serializing.serialize(world.World())
    store = storage.HttpStorage("http://127.0.0.1:45600")
    key = shortuuid.uuid()
    serialized = await store.update({storage.Keys(key, 0): serialized})
    assert serialized == 1
    serialized = await store.update({storage.Keys(key, None): None})
    assert serialized == 1
