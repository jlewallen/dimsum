from typing import Dict, List, Optional

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
