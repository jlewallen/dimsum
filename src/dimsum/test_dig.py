import pytest
import logging

import entity
import game
import things
import world
import reply
import serializing
import persistence
import test

log = logging.getLogger("dimsum")


@pytest.mark.asyncio
async def test_dig_north_single_quotes():
    tw = test.TestWorld()
    await tw.initialize()
    await tw.success("dig north to 'Canada'")


@pytest.mark.asyncio
async def test_dig_north_double_quotes():
    tw = test.TestWorld()
    await tw.initialize()
    await tw.success('dig north to "Canada"')
