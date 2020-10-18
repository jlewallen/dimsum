import sys
import logging
import pytest

import props
import game
import actions
import test


@pytest.mark.asyncio
async def test_drop_hammer_funny_gold(caplog):
    tw = test.TestWorld()

    hammer = tw.add_item(game.Item(creator=tw.jacob, details=props.Details("Hammer")))
    hammer.add_behavior(
        "b:test:drop:after",
        lua="""
function(s, world, area, player)
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

    cape = tw.add_item(game.Item(creator=tw.jacob, details=props.Details("Cape")))
    cape.link_activity("worn")
    cape.add_behavior(
        "b:test:wear:after",
        lua="""
function(s, world, area, player)
    player.invisible()
    debug(player.is_invisible())
end
""",
    )
    cape.add_behavior(
        "b:test:remove:after",
        lua="""
function(s, world, area, player)
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


@pytest.mark.asyncio
async def test_behavior_move(caplog):
    caplog.set_level(logging.INFO)
    tw = test.TestWorld()

    mystery_area = game.Area(creator=tw.player, details=props.Details("A Mystery Area"))
    tw.world.register(mystery_area)

    cape = tw.add_item(game.Item(creator=tw.jacob, details=props.Details("Cape")))
    cape.link_activity("worn", mystery_area)
    cape.add_behavior(
        "b:test:wear:after",
        lua="""
function(s, world, area, player)
    debug('wear', wear)
    debug('wear[0].worn', wear[0].worn)
    return player.go(wear[0].worn)
end
""",
    )

    await tw.initialize()
    await tw.execute("look")
    await tw.execute("hold cape")
    await tw.execute("wear cape")
    await tw.execute("look")

    assert tw.world.find_player_area(tw.player) == mystery_area


@pytest.mark.asyncio
async def test_behavior_create_item(caplog):
    caplog.set_level(logging.INFO)
    tw = test.TestWorld()

    box = tw.add_item(
        game.Item(creator=tw.jacob, details=props.Details("A Colorful Box"))
    )
    box.add_behavior(
        "b:test:shake:after",
        lua="""
function(s, world, area, player)
    debug(area)
    return player.make({
        name = "Flower Petal",
        color = "red",
    })
end
""",
    )

    await tw.initialize()
    await tw.execute("look")
    await tw.execute("hold box")
    assert len(tw.player.holding) == 1
    await tw.execute("shake box")
    assert len(tw.player.holding) == 2
    assert tw.player.holding[1].creator == tw.player
    await tw.execute("look")


@pytest.mark.asyncio
async def test_behavior_create_quantified_item(caplog):
    caplog.set_level(logging.INFO)
    tw = test.TestWorld()

    box = tw.add_item(
        game.Item(creator=tw.jacob, details=props.Details("A Colorful Box"))
    )
    box.add_behavior(
        "b:test:shake:after",
        lua="""
function(s, world, area, player)
    debug(area)
    return area.make({
        name = "Flower Petal",
        quantity = 10,
        color = "red",
    })
end
""",
    )

    await tw.initialize()
    await tw.execute("look")
    await tw.execute("hold box")
    assert len(tw.player.holding) == 1
    assert len(tw.area.items) == 0
    await tw.execute("shake box")
    assert len(tw.player.holding) == 1
    assert len(tw.area.items) == 1
    assert tw.area.items[0].creator == box
    assert tw.area.items[0].quantity == 10
    await tw.execute("look")


@pytest.mark.asyncio
async def test_behavior_create_area(caplog):
    pass


@pytest.mark.asyncio
async def test_behavior_time_passing(caplog):
    caplog.set_level(logging.INFO)
    tw = test.TestWorld()

    tree = tw.add_item(
        game.Item(creator=tw.jacob, details=props.Details("A Lovely Tree"))
    )
    tree.add_behavior(
        "b:test:tick",
        lua="""
function(s, world, area, item)
    debug("ok", area, item, time)
    return area.make({
        name = "Flower Petal",
        quantity = 10,
        color = "red",
    })
end
""",
    )

    await tw.initialize()
    await tw.world.tick(0)
    assert len(tw.area.items) == 2
    assert len(tw.world.items()) == 2

    await tw.world.tick(1)
    assert len(tw.area.items) == 3
    assert len(tw.world.items()) == 3


@pytest.mark.asyncio
async def test_behavior_create_kind(caplog):
    caplog.set_level(logging.INFO)
    tw = test.TestWorld()

    tree = tw.add_item(
        game.Item(creator=tw.jacob, details=props.Details("A Lovely Tree"))
    )
    tree.add_behavior(
        "b:test:tick",
        lua="""
function(s, world, area, item)
    debug("ok", area, item, time)
    return area.make({
        kind = item.kind("petals"),
        name = "Flower Petal",
        quantity = 10,
        color = "red",
    })
end
""",
    )

    await tw.initialize()
    await tw.world.tick(0)
    assert len(tw.area.items) == 2
    assert len(tw.world.items()) == 2
    await tw.world.tick(1)
    assert len(tw.area.items) == 2
    assert len(tw.world.items()) == 2
    await tw.world.tick(2)
    assert len(tw.area.items) == 2
    assert len(tw.world.items()) == 2

    
@pytest.mark.asyncio
async def test_behavior_random(caplog):
    caplog.set_level(logging.INFO)
    tw = test.TestWorld()

    tree = tw.add_item(
        game.Item(creator=tw.jacob, details=props.Details("A Lovely Tree"))
    )
    tree.add_behavior(
        "b:test:tick",
        lua="""
function(s, world, area, item)
    debug("random", math.random())
end
""",
    )

    await tw.initialize()
    await tw.world.tick(0)
