import logging
import pytest

import handlers
import model.visual as visual

import test
from test_utils import *

log = logging.getLogger("dimsum")


@pytest.mark.asyncio
async def test_edit_thing_missing():
    tw = test.TestWorld(handlers=[handlers.create(visual.NoopComms())])
    await tw.initialize()
    await tw.failure("edit box")


@pytest.mark.asyncio
async def test_edit_here():
    tw = test.TestWorld(handlers=[handlers.create(visual.NoopComms())])
    await tw.initialize()
    await tw.success("edit here")


@pytest.mark.asyncio
async def test_edit_item():
    tw = test.TestWorld(handlers=[handlers.create(visual.NoopComms())])
    await tw.initialize()
    await tw.success("create thing Box")
    await tw.success("edit box")


@pytest.mark.asyncio
async def test_edit_item_with_error_in_dynamic_leaves_version_unchanged(
    silence_dynamic_errors,
):
    tw = test.TestWorld(handlers=[handlers.create(visual.NoopComms())])
    await tw.initialize()

    box = await tw.add_behaviored_thing(
        tw,
        "Box",
        """
og.info("hello")
""",
    )

    await tw.success("edit box")

    with tw.domain.session() as session:
        box = await session.materialize(key=box.key)
        assert box.version.i == 2

    await tw.success("edit box")

    with tw.domain.session() as session:
        box = await session.materialize(key=box.key)
        assert box.version.i == 2
