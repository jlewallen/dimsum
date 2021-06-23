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


class Server(uvicorn.Server):
    def install_signal_handlers(self):
        pass

    @contextlib.contextmanager
    def run_in_thread(self):
        thread = threading.Thread(target=self.run)
        thread.start()
        try:
            while not self.started:
                time.sleep(1e-3)
            yield
        finally:
            self.should_exit = True
            thread.join()


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
    await store.number_of_entities()


@pytest.mark.asyncio
async def test_storage_http_purge(server):
    store = storage.HttpStorage("http://127.0.0.1:45600")
    await store.purge()


@pytest.mark.asyncio
async def test_storage_load_by_key(server):
    store = storage.HttpStorage("http://127.0.0.1:45600")
    await store.load_by_key("world")
