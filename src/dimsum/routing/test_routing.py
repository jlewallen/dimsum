from typing import Dict, List, Optional

import os
import sys
import abc
import json
import logging
import pytest

from routing import *

log = logging.getLogger("dimsum")


@pytest.mark.asyncio
async def test_routing_empty():
    router = Router()
    with pytest.raises(NoRoutesException):
        await router.handle("{}")


@pytest.mark.asyncio
async def test_routing_single_target():
    router = Router(targets=[AlwaysOkTarget()])
    reply = await router.handle("{}")
    assert reply == json.dumps({"ok": True})


@pytest.mark.asyncio
async def test_routing_process_target_cat():
    router = Router(targets=[ProcessTarget(command=["/bin/cat"])])
    reply = await router.handle("{}")
    assert reply == "{}"


@pytest.mark.asyncio
async def test_routing_process_target_query_fail_no_query():
    router = Router(targets=[ProcessTarget(command=["src/dimsum/cli.py", "query"])])
    reply = await router.handle("{}")
    assert reply == '{"errors": [{"message": "query is required"}]}'


@pytest.mark.asyncio
async def test_routing_process_target_query_entity():
    router = Router(targets=[ProcessTarget(command=["src/dimsum/cli.py", "query"])])
    query = """
{
    entities(entityKey: "world") {
        key
    }
}
"""
    reply = await router.handle(json.dumps({"query": query}))
    assert json.loads(reply) == {"data": {"entities": [{"key": "world"}]}}
