import sys
import logging
import pytest

import game
import props
import test


@pytest.mark.asyncio
async def test_simple_behavior(caplog):
    tw = test.TestWorld()

    hammer = tw.add_item(game.Item(owner=tw.jacob, details=props.Details("Hammer")))
    hammer.add_behavior(
        "b:test:drop:after",
        lua="""
function(s, world, player)
    if not player.gold then
        player.gold = { total = 0 }
    end
    if player.gold.total < 2 then
        player.gold.total = player.gold.total + 1
    else
        debug("yes!")
    end
    debug("ok")
end
""",
    )

    await tw.initialize()
    await tw.execute("look")
    await tw.execute("hold hammer")
    await tw.execute("drop")
    await tw.execute("hold hammer")
    await tw.execute("drop")
    await tw.execute("hold hammer")
    await tw.execute("drop")

    assert tw.jacob.details["gold"]["total"] == 2
