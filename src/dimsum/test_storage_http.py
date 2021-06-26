from typing import Dict, List, Optional
from multiprocessing import Process

import json
import logging
import pytest
import uvicorn
import contextlib
import time

import storage
import dimsum

log = logging.getLogger("dimsum")


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
    yield
    proc.kill()


@pytest.mark.asyncio
async def test_server(server):
    pass


@pytest.mark.asyncio
async def test_storage_http_number_of_entities(server):
    store = storage.HttpStorage("http://127.0.0.1:45600")
    size = await store.number_of_entities()
    assert size == 61


@pytest.mark.asyncio
async def test_storage_http_purge(server):
    store = storage.HttpStorage("http://127.0.0.1:45600")
    await store.purge()


@pytest.mark.asyncio
async def test_storage_load_by_key(server):
    store = storage.HttpStorage("http://127.0.0.1:45600")
    serialized = await store.load_by_key("world")
    assert [json.loads(s.serialized) for s in serialized]


@pytest.mark.asyncio
async def test_storage_load_by_gid(server):
    store = storage.HttpStorage("http://127.0.0.1:45600")
    serialized = await store.load_by_gid(0)
    assert [json.loads(s.serialized) for s in serialized]


@pytest.mark.asyncio
async def test_storage_update_entity(server):
    store = storage.HttpStorage("http://127.0.0.1:45600")
    serialized = await store.load_by_gid(0)
    assert [json.loads(s.serialized) for s in serialized]
