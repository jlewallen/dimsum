from typing import Dict, List, Optional

import json
import logging
import pytest
import freezegun

import routing


@pytest.mark.asyncio
@pytest.mark.skip(reason="create sample world")
@freezegun.freeze_time("2019-09-25")
async def test_routing_process_target_query_fail_no_query(snapshot):
    store = storage.SqliteStorage("test.sqlite3")
    await store.purge()
    await test.make_simple_domain(store=store)

    router = routing.Router(
        targets=[
            routing.ProcessTarget(
                command=["src/dimsum/cli.py", "query", "--database", "test.sqlite3"]
            )
        ]
    )
    reply = await router.handle("{}")
    snapshot.assert_match(reply, "stdout.json")


@pytest.mark.asyncio
@pytest.mark.skip(reason="create sample world")
@freezegun.freeze_time("2019-09-25")
async def test_routing_process_target_query_entity(snapshot):
    store = storage.SqliteStorage("test.sqlite3")
    await store.purge()
    await test.make_simple_domain(store=store)

    router = routing.Router(
        targets=[
            routing.ProcessTarget(
                command=["src/dimsum/cli.py", "query", "--database", "test.sqlite3"]
            )
        ]
    )
    query = '{ entitiesByKey(key: "world") }'
    reply = await router.handle(json.dumps({"query": query}))
    snapshot.assert_match(reply, "stdout.json")
