import pytest

import handlers
from model import *
import test
from test_utils import *


@pytest.mark.asyncio
async def test_edit_thing_missing():
    tw = test.TestWorld(handlers=[handlers.create(NoopComms())])
    await tw.initialize()
    await tw.failure("edit box")


@pytest.mark.asyncio
async def test_edit_here():
    tw = test.TestWorld(handlers=[handlers.create(NoopComms())])
    await tw.initialize()
    await tw.success("edit here")


@pytest.mark.asyncio
async def test_edit_item():
    tw = test.TestWorld(handlers=[handlers.create(NoopComms())])
    await tw.initialize()
    await tw.success("create thing Box")
    await tw.success("edit box")


@pytest.mark.asyncio
async def test_edit_item_with_error_in_dynamic_leaves_version_unchanged(
    silence_dynamic_errors,
):
    tw = test.TestWorld(handlers=[handlers.create(NoopComms())])
    await tw.initialize()

    box_key = await tw.add_behaviored_thing(
        "Box",
        """
og.info("hello")
""",
    )

    await tw.success("edit box")

    with tw.domain.session() as session:
        box = await session.materialize(key=box_key)
        assert box.version.i == 3

    await tw.success("edit box")

    with tw.domain.session() as session:
        box = await session.materialize(key=box_key)
        assert box.version.i == 3
