import asyncio
import json
import logging
import time
import shortuuid
import uvicorn
import pytest
import freezegun
import ariadne.asgi
import jwt
from typing import Optional, List
from multiprocessing import Process
from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport

import serializing
import config
import storage
from loggers import get_logger
from model import *
import schema as schema_factory
import test

log = get_logger("dimsum")
session_key = "asdfasdf"


@pytest.fixture(scope="function")
def silence_aihttp(caplog):
    caplog.set_level(logging.CRITICAL, "gql.transport.aiohttp")
    yield


def session(url: str, key: str = "jlewallen"):
    global session_key
    jwt_token = jwt.encode(dict(key=key), session_key, algorithm="HS256")
    return Client(
        transport=AIOHTTPTransport(
            url=url, headers={"Authorization": "Bearer %s" % (jwt_token,)}
        ),
        fetch_schema_from_transport=True,
    )


async def initialize(url: str):
    async with session(url) as s:
        query = gql("mutation { makeSample { affected { key } } }")
        await s.execute(query)


def app():
    global session_key
    log.info("starting test server")
    cfg = config.symmetrical(":memory:", session_key=session_key)
    schema = schema_factory.create()
    domain = cfg.make_domain()
    get_logger("ariadne.silenced").setLevel(logging.CRITICAL)
    return ariadne.asgi.GraphQL(
        schema,
        context_value=schema_factory.context(cfg, domain),
        debug=True,
        logger="ariadne.silenced",
    )


@pytest.fixture(scope="session")
def server():
    log.info("starting server")
    proc = Process(
        target=uvicorn.run,
        args=(app,),
        kwargs={
            "host": "127.0.0.1",
            "port": 45600,
            "log_level": "critical",
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


def get_token(key: str, session_key="asdfasdf"):
    return jwt.encode(dict(key=key), session_key, algorithm="HS256")


@pytest.mark.asyncio
async def test_storage_http_number_of_entities(server, silence_aihttp):
    store = storage.HttpStorage("http://127.0.0.1:45600", get_token("jlewallen"))
    size = await store.number_of_entities()
    assert size == 70


@pytest.mark.asyncio
async def test_storage_load_by_key(server, silence_aihttp):
    store = storage.HttpStorage("http://127.0.0.1:45600", get_token("jlewallen"))
    serialized = await store.load_by_key("world")
    assert [json.loads(s.serialized) for s in serialized]


@pytest.mark.asyncio
async def test_storage_load_by_gid(server, silence_aihttp):
    store = storage.HttpStorage("http://127.0.0.1:45600", get_token("jlewallen"))
    serialized = await store.load_by_gid(0)
    assert [json.loads(s.serialized) for s in serialized]


@pytest.mark.asyncio
async def test_storage_update_nothing(server, silence_aihttp):
    store = storage.HttpStorage("http://127.0.0.1:45600", get_token("jlewallen"))
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
    key = shortuuid.uuid(name="example-1")
    e = Entity(key=key, creator=World(), props=Common(name="Fake Entity"))
    serialized = serializing.serialize(e, identities=serializing.Identities.PRIVATE)
    assert serialized

    store = storage.HttpStorage("http://127.0.0.1:45600", get_token("jlewallen"))

    updated = await store.update({key: CompiledJson.compile(serialized)})
    snapshot.assert_match(test.pretty_json(updated, deterministic=True), "before.json")

    e.version.increase()
    serialized = serializing.serialize(e, identities=serializing.Identities.PRIVATE)
    assert serialized

    updated = await store.update({key: CompiledJson.compile(serialized)})
    snapshot.assert_match(test.pretty_json(updated, deterministic=True), "after.json")

    loaded: List[Serialized] = await store.load_by_key(key)
    snapshot.assert_match(
        test.pretty_json({v.key: v.serialized for v in loaded}, deterministic=True),
        "queried.json",
    )


@pytest.mark.asyncio
@freezegun.freeze_time("2019-09-25")
async def test_storage_delete_one_entity(
    snapshot, server, silence_aihttp, deterministic, caplog
):
    key = shortuuid.uuid(name="example-2")
    e = Entity(key=key, creator=World(), props=Common(name="Fake Entity"))
    serialized = serializing.serialize(e, identities=serializing.Identities.PRIVATE)
    assert serialized

    store = storage.HttpStorage("http://127.0.0.1:45600", get_token("jlewallen"))
    updated = await store.update({key: CompiledJson.compile(serialized)})
    snapshot.assert_match(test.pretty_json(updated, deterministic=True), "before.json")

    e.version.increase()
    e.destroy()
    serialized = serializing.serialize(e, identities=serializing.Identities.PRIVATE)
    assert serialized

    updated = await store.update({key: CompiledJson.compile(serialized)})
    snapshot.assert_match(test.pretty_json(updated, deterministic=True), "after.json")

    with pytest.raises(Exception) as ex:
        with caplog.at_level(logging.CRITICAL):
            await store.load_by_key(key)

    assert "MissingEntityException" in str(ex)
