from typing import Dict, List, Optional

import json
import logging
import pytest

import storage

log = logging.getLogger("dimsum")


@pytest.mark.asyncio
async def test_storage_http_number_of_entities():
    store = storage.HttpStorage("http://127.0.0.1:8000")
    await store.number_of_entities()


@pytest.mark.asyncio
async def test_storage_http_purge():
    store = storage.HttpStorage("http://127.0.0.1:8000")
    await store.purge()


@pytest.mark.asyncio
async def test_storage_load_by_key():
    store = storage.HttpStorage("http://127.0.0.1:8000")
    await store.load_by_key("world")
