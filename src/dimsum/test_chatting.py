import pytest

import handlers
from model import *
import test


@pytest.mark.asyncio
async def test_say_nothing():
    tw = test.TestWorld(handlers=[handlers.create(NoopComms())])
    await tw.initialize()
    await tw.failure("say")
    await tw.close()


@pytest.mark.asyncio
async def test_say_basic():
    tw = test.TestWorld(handlers=[handlers.create(NoopComms())])
    await tw.initialize()
    await tw.success("say hello, world!")
    await tw.close()


@pytest.mark.asyncio
async def test_say_with_initial_quote():
    tw = test.TestWorld(handlers=[handlers.create(NoopComms())])
    await tw.initialize()
    await tw.success('" hello, world!')
    await tw.close()
