import pytest
import logging

import props
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
async def test_hold_missing_item():
    tw = test.TestWorld()
    await tw.initialize()
    await tw.failure("hold hammer")
    assert len(tw.player.holding) == 0


@pytest.mark.asyncio
async def test_make_hold_drop():
    tw = test.TestWorld()
    await tw.initialize()
    await tw.success("make Hammer")
    assert len(tw.player.holding) == 1
    await tw.success("drop")
    assert len(tw.player.holding) == 0
    await tw.success("hold hammer")
    assert len(tw.player.holding) == 1


@pytest.mark.asyncio
async def test_make_hold_drop_specific():
    tw = test.TestWorld()
    await tw.initialize()
    await tw.success("make Hammer")
    await tw.success("make Ball")
    assert len(tw.player.holding) == 2
    await tw.success("drop ball")
    assert len(tw.player.holding) == 1
    await tw.success("hold ball")
    assert len(tw.player.holding) == 2


@pytest.mark.asyncio
async def test_put_coin_inside_box_and_then_take_out(caplog):
    caplog.set_level(logging.INFO)
    tw = test.TestWorld()
    await tw.initialize()
    await tw.success("make Coin")
    await tw.success("make Box")
    assert len(tw.player.holding) == 2
    await tw.success("put coin in box")
    assert len(tw.player.holding) == 1
    await tw.success("look down")
    assert len(tw.world.find_entity_by_name("Box").holding) == 1
    await tw.success("take coin out of box")
    assert len(tw.world.find_entity_by_name("Box").holding) == 0
    assert len(tw.player.holding) == 2


@pytest.mark.asyncio
async def test_lock_with_new_key(caplog):
    caplog.set_level(logging.INFO)
    tw = test.TestWorld()
    await tw.initialize()
    await tw.success("make Box")
    await tw.success("lock box")
    assert len(tw.player.holding) == 2
    await tw.success("unlock box")
    assert len(tw.player.holding) == 2
    await tw.success("lock box with key")
    assert len(tw.player.holding) == 2
    await tw.success("unlock box")
    assert len(tw.player.holding) == 2


@pytest.mark.asyncio
async def test_try_unlock_wrong_key(caplog):
    caplog.set_level(logging.INFO)
    tw = test.TestWorld()
    await tw.initialize()
    await tw.success("make Box")
    await tw.success("lock box")
    assert len(tw.player.holding) == 2
    await tw.success("drop key")
    assert len(tw.player.holding) == 1

    await tw.success("make Chest")
    await tw.success("lock chest")
    await tw.success("drop chest")
    await tw.failure("unlock box with key")


@pytest.mark.asyncio
async def test_make_and_open_container(caplog):
    tw = test.TestWorld()
    await tw.initialize()
    await tw.success("make Box")
    await tw.failure("close box")
    await tw.success("open box")
    await tw.success("close box")
    await tw.success("open box")
    await tw.success("close box")
