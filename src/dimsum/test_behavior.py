import sys
import logging
import pytest

import properties
import game
import things
import envo
import actions
import test


@pytest.mark.asyncio
async def test_drop_hammer_funny_gold(caplog):
    tw = test.TestWorld()
    await tw.initialize()

    hammer = tw.add_item(
        things.Item(creator=tw.jacob, props=properties.Common("Hammer"))
    )
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

    await tw.success("look")
    await tw.success("hold hammer")
    await tw.success("drop")
    await tw.success("hold hammer")
    await tw.success("drop")
    await tw.success("hold hammer")
    await tw.success("drop")

    assert tw.jacob.props["gold"]["total"] == 2


@pytest.mark.asyncio
async def test_wear_cape(caplog):
    tw = test.TestWorld()
    await tw.initialize()

    cape = tw.add_item(things.Item(creator=tw.jacob, props=properties.Common("Cape")))
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

    await tw.success("look")
    await tw.success("hold cape")
    await tw.success("wear cape")
    assert tw.jacob.is_invisible
    await tw.success("remove cape")
    assert not tw.jacob.is_invisible
    await tw.success("drop")


@pytest.mark.asyncio
async def test_behavior_move(caplog):
    tw = test.TestWorld()
    await tw.initialize()

    mystery_area = envo.Area(
        creator=tw.player, props=properties.Common("A Mystery Area")
    )
    tw.world.register(mystery_area)

    cape = tw.add_item(things.Item(creator=tw.jacob, props=properties.Common("Cape")))
    cape.link_activity("worn", mystery_area)
    cape.add_behavior(
        "b:test:wear:after",
        lua="""
function(s, world, area, player)
    debug('wear[0].worn', wear[0].interactions.worn)
    return player.go(wear[0].interactions.worn)
end
""",
    )

    await tw.success("look")
    await tw.success("hold cape")
    await tw.success("wear cape")
    await tw.success("look")

    assert tw.world.find_player_area(tw.player) == mystery_area


@pytest.mark.asyncio
async def test_behavior_create_item(caplog):
    tw = test.TestWorld()
    await tw.initialize()

    box = tw.add_item(
        things.Item(creator=tw.jacob, props=properties.Common("A Colorful Box"))
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

    await tw.success("look")
    await tw.success("hold box")
    assert len(tw.player.holding) == 1
    await tw.success("shake box")
    assert len(tw.player.holding) == 2
    assert tw.player.holding[1].creator == tw.player
    await tw.success("look")


@pytest.mark.asyncio
async def test_behavior_create_quantified_item(caplog):
    tw = test.TestWorld()
    await tw.initialize()

    box = tw.add_item(
        things.Item(creator=tw.jacob, props=properties.Common("A Colorful Box"))
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

    await tw.success("look")
    await tw.success("hold box")
    assert len(tw.player.holding) == 1
    assert len(tw.area.entities()) == 1
    await tw.success("shake box")
    assert len(tw.player.holding) == 1
    assert len(tw.area.entities()) == 2
    assert tw.area.entities()[0].creator == box
    assert tw.area.entities()[0].quantity == 10
    await tw.success("look")


@pytest.mark.asyncio
async def test_behavior_create_area(caplog):
    pass


@pytest.mark.asyncio
async def test_behavior_time_passing(caplog):
    tw = test.TestWorld()
    await tw.initialize()

    tree = tw.add_item(
        things.Item(creator=tw.jacob, props=properties.Common("A Lovely Tree"))
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

    await tw.world.tick(0)
    assert len(tw.area.entities()) == 3
    assert len(tw.world.items()) == 2

    await tw.world.tick(1)
    assert len(tw.area.entities()) == 4
    assert len(tw.world.items()) == 3


@pytest.mark.asyncio
async def test_behavior_create_kind(caplog):
    tw = test.TestWorld()
    await tw.initialize()

    tree = tw.add_item(
        things.Item(creator=tw.jacob, props=properties.Common("A Lovely Tree"))
    )
    tree.add_behavior(
        "b:test:tick",
        lua="""
function(s, world, area, item)
    return area.make({
        kind = item.kind("petals"),
        name = "Flower Petal",
        quantity = 10,
        color = "red",
    })
end
""",
    )

    await tw.world.tick(0)
    assert len(tw.area.entities()) == 3
    assert len(tw.world.items()) == 2
    await tw.world.tick(1)
    assert len(tw.area.entities()) == 3
    assert len(tw.world.items()) == 2
    await tw.world.tick(2)
    assert len(tw.area.entities()) == 3
    assert len(tw.world.items()) == 2


@pytest.mark.asyncio
async def test_behavior_random(caplog):
    tw = test.TestWorld()
    await tw.initialize()

    tree = tw.add_item(
        things.Item(creator=tw.jacob, props=properties.Common("A Lovely Tree"))
    )
    tree.add_behavior(
        "b:test:tick",
        lua="""
function(s, world, area, item)
    debug("random", math.random())
end
""",
    )

    await tw.world.tick(0)


@pytest.mark.asyncio
async def test_behavior_numbering_by_kind(caplog):
    tw = test.TestWorld()
    await tw.initialize()

    tree = tw.add_item(
        things.Item(creator=tw.jacob, props=properties.Common("A Lovely Tree"))
    )
    tree.add_behavior(
        "b:test:tick",
        lua="""
function(s, world, area, item)
    if area.number(item.kind("petals")) == 0 then
        return area.make({
            kind = item.kind("petals"),
            name = "Flower Petal",
            quantity = 10,
            color = "red",
        })
    else
        return area.make({
            kind = item.kind("leaves"),
            name = "Oak Leaves",
            quantity = 10,
            color = "red",
        })
    end
end
""",
    )

    await tw.world.tick(0)
    assert len(tw.area.entities()) == 3
    await tw.world.tick(1)
    assert len(tw.area.entities()) == 4


@pytest.mark.asyncio
async def test_behavior_numbering_person_by_name(caplog):
    tw = test.TestWorld()
    await tw.initialize()

    tree = tw.add_item(
        things.Item(creator=tw.jacob, props=properties.Common("A Lovely Tree"))
    )
    tree.add_behavior(
        "b:test:tick",
        lua="""
function(s, world, area, item)
    if area.number("Jacob") == 0 then
        return area.make({
            kind = item.kind("leaves"),
            name = "Oak Leaves",
            quantity = 10,
            color = "red",
        })
    end
end
""",
    )

    await tw.world.tick(0)
    assert len(tw.area.entities()) == 2
    await tw.world.tick(1)
    assert len(tw.area.entities()) == 2
