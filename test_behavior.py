import sys
import logging
import pytest

import game
import props
import test


@pytest.mark.asyncio
async def test_drop_hammer_funny_gold(caplog):
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


@pytest.mark.asyncio
async def test_wear_cape(caplog):
    caplog.set_level(logging.INFO)
    tw = test.TestWorld()

    cape = tw.add_item(game.Item(owner=tw.jacob, details=props.Details("Cape")))
    cape.link_activity("worn")
    cape.add_behavior(
        "b:test:wear:after",
        lua="""
function(s, world, player)
    player.invisible()
    debug(player.is_invisible())
end
""",
    )
    cape.add_behavior(
        "b:test:remove:after",
        lua="""
function(s, world, player)
    player.visible()
end
""",
    )

    await tw.initialize()
    await tw.execute("look")
    await tw.execute("hold cape")
    await tw.execute("wear cape")
    assert tw.jacob.visible == {"hidden": True}
    await tw.execute("remove cape")
    assert tw.jacob.visible == {}
    await tw.execute("drop")
