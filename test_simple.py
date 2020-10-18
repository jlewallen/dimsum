import pytest
import logging

import props
import entity
import game
import serializing
import persistence
import test

log = logging.getLogger("dimsum")


@pytest.mark.asyncio
async def test_hold_missing_item():
    tw = test.TestWorld()
    await tw.initialize()
    await tw.execute("hold hammer")
    assert len(tw.player.holding) == 0


@pytest.mark.asyncio
async def test_make_hold_drop():
    tw = test.TestWorld()
    await tw.initialize()
    await tw.execute("make Hammer")
    assert len(tw.player.holding) == 1
    await tw.execute("drop")
    assert len(tw.player.holding) == 0
    await tw.execute("hold hammer")
    assert len(tw.player.holding) == 1


@pytest.mark.asyncio
async def test_make_hold_drop_specific():
    tw = test.TestWorld()
    await tw.initialize()
    await tw.execute("make Hammer")
    await tw.execute("make Ball")
    assert len(tw.player.holding) == 2
    await tw.execute("drop ball")
    assert len(tw.player.holding) == 1
    await tw.execute("hold ball")
    assert len(tw.player.holding) == 2


@pytest.mark.asyncio
async def test_simple_action_verbs():
    tw = test.TestWorld()
    await tw.initialize()
    await tw.add_carla()
    for verb in ["kiss", "kick", "heal", "hug", "tickle", "poke"]:
        await tw.execute(verb + " carla")
    assert len(tw.player.holding) == 0


@pytest.mark.asyncio
async def test_obliterate():
    tw = test.TestWorld()
    await tw.initialize()
    await tw.execute("make Hammer")
    assert len(tw.player.holding) == 1
    await tw.execute("obliterate")
    assert len(tw.player.holding) == 0


@pytest.mark.asyncio
async def test_recipe_simple():
    tw = test.TestWorld()
    await tw.initialize()
    await tw.execute("make IPA")
    await tw.execute("modify alcohol 100")
    assert tw.player.holding[0].details["alcohol"] == 100

    assert len(tw.player.memory.keys()) == 0
    await tw.execute("call this Fancy IPA")
    assert len(tw.player.memory.keys()) == 1

    await tw.execute("make fancy")
    assert len(tw.player.holding) == 1


@pytest.mark.asyncio
async def test_look_for():
    tw = test.TestWorld()
    await tw.initialize()
    await tw.execute("look for keys")


@pytest.mark.asyncio
async def test_look_empty():
    tw = test.TestWorld()
    await tw.initialize()
    r = await tw.execute("look")
    assert isinstance(r, game.AreaObservation)
    assert len(r.items) == 0
    assert len(r.people) == 0


@pytest.mark.asyncio
async def test_look_items():
    tw = test.TestWorld()
    await tw.initialize()
    await tw.execute("make IPA")
    await tw.execute("drop")
    r = await tw.execute("look")
    assert isinstance(r, game.AreaObservation)
    assert len(r.items) == 1
    assert len(r.people) == 0


@pytest.mark.asyncio
async def test_look_people():
    tw = test.TestWorld()
    await tw.initialize()
    await tw.add_carla()
    r = await tw.execute("look")
    assert isinstance(r, game.AreaObservation)
    assert len(r.items) == 0
    assert len(r.people) == 1


@pytest.mark.asyncio
async def test_look_people_invisible():
    tw = test.TestWorld()
    await tw.initialize()
    await tw.add_tomi()
    await tw.add_carla()
    tw.carla.make_invisible()

    r = await tw.execute("look")
    assert isinstance(r, game.AreaObservation)
    assert len(r.items) == 0
    assert len(r.people) == 1


@pytest.mark.asyncio
async def test_think():
    tw = test.TestWorld()
    await tw.initialize()

    await tw.execute("think")


@pytest.mark.asyncio
async def test_serialize():
    tw = test.TestWorld()
    await tw.initialize()

    tree = tw.add_item(
        game.Item(creator=tw.jacob, details=props.Details("A Lovely Tree"))
    )
    clearing = tw.add_simple_area_here("Door", "Clearing")
    tree.get_kind("petals")
    tree.link_area(clearing)
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

    db = persistence.SqliteDatabase()
    await db.open("test.sqlite3")
    await db.save(tw.world)

    empty = game.World(tw.bus, context_factory=None)
    await db.load(empty)

    logging.info("%s", empty.entities)


@pytest.mark.asyncio
async def test_unregister_destroys(caplog):
    caplog.set_level(logging.INFO)
    tw = test.TestWorld()
    await tw.initialize()

    db = persistence.SqliteDatabase()
    await db.open("test.sqlite3")
    await db.purge()

    assert await db.number_of_entities() == 0

    await tw.initialize()
    await tw.execute("make Box")
    box = tw.player.holding[0]
    assert box.destroyed == False
    await db.save(tw.world)

    assert await db.number_of_entities() == 3

    await tw.execute("obliterate")
    assert box.destroyed == True
    await db.save(tw.world)

    assert await db.number_of_entities() == 2

    empty = game.World(tw.bus, context_factory=None)
    await db.load(empty)
