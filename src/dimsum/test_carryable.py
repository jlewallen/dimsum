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
async def test_put_coin_inside_box_and_then_take_out(caplog):
    caplog.set_level(logging.INFO)
    tw = test.TestWorld()
    await tw.initialize()
    await tw.execute("make Coin")
    await tw.execute("make Box")
    assert len(tw.player.holding) == 2
    await tw.execute("put coin in box")
    assert len(tw.player.holding) == 1
    await tw.execute("look down")
    assert len(tw.world.find_entity_by_name("Box").holding) == 1
    await tw.execute("take coin out of box")
    assert len(tw.world.find_entity_by_name("Box").holding) == 0
    assert len(tw.player.holding) == 2
