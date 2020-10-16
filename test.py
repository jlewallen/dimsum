import asyncio
import logging
import sys
import lupa
import lark

import crypto

from props import *
from persistence import *
from game import *
from grammar import *
from evaluator import *
from behavior import *
from actions import *


l = create_parser()


async def execute(world, player, tree):
    action = create(world, player).transform(tree)
    if action:
        return await world.perform(player, action)
    return None


async def test_run():
    bus = EventBus()
    world = World(bus)

    jacob = Player(owner=world, details=Details("Jacob", desc="Curly haired bastard."))
    carla = Player(owner=world, details=Details("Carla", desc="Chief salad officer."))
    hammer = Item(owner=jacob, details=Details("Hammer", desc="It's heavy."))

    world.add_area(Area(owner=jacob, details=Details("Living room")).add_item(hammer))
    world.add_area(Area(owner=jacob, details=Details("Kitchen")))
    await world.perform(jacob, actions.Join())
    await world.perform(carla, actions.Join())

    logging.info(world.look(jacob))
    logging.info(world.look(carla))

    await world.perform(jacob, actions.Hold(item=hammer))

    logging.info(world.look(jacob))
    logging.info(world.look(carla))

    trampoline = Item(owner=jacob, details=Details("Trampoline", desc="It's bouncy."))

    await world.perform(jacob, actions.Make(item=trampoline))
    await world.perform(jacob, actions.Drop())
    await world.perform(jacob, actions.Hold(item=trampoline))
    await world.perform(jacob, actions.Drop())

    idea = Item(owner=jacob, details=Details("Idea", desc="It's genius."))
    await world.perform(jacob, actions.Make(item=idea))
    logging.info(world.look(jacob))
    await world.perform(jacob, actions.Drop())

    door = Item(owner=jacob, details=Details("Door", desc="It's wooden."))
    await world.perform(jacob, actions.Make(item=door))
    await world.perform(jacob, actions.Go(item=door))
    logging.info(world.look(jacob))
    await world.perform(jacob, actions.Go(item=door))
    logging.info(world.look(jacob))

    logging.info("saving and reloading")

    db = SqlitePersistence()

    await db.open("test.sqlite3")
    await db.save(world)
    restored = World(bus)
    await db.load(restored)
    logging.info(restored.look(restored.players()[0]))

    l = create_parser()

    logging.info(l.parse("drop"))
    logging.info(l.parse("obliterate"))
    logging.info(l.parse("look"))
    logging.info(l.parse("hold my beer"))
    logging.info(l.parse("make My Beer"))
    logging.info(l.parse("remember"))
    logging.info(l.parse("modify name Rusty Hammer"))
    logging.info(l.parse("modify desc How could anyone use this?"))
    logging.info(l.parse("modify when opened"))
    logging.info(l.parse("modify when eaten"))
    logging.info(l.parse("modify capacity 100"))
    logging.info(l.parse("look at ipa"))
    logging.info(l.parse("look at myself"))
    logging.info(l.parse("go window"))
    logging.info(l.parse("kiss carla"))
    logging.info(l.parse("call this IPA"))
    logging.info(l.parse("forget ipa"))
    logging.info(l.parse("plant"))
    logging.info(l.parse("plant this"))
    logging.info(l.parse("plant seeds"))
    logging.info(l.parse("water seeds"))
    logging.info(l.parse("pour water over seeds"))
    logging.info(l.parse("hit myself with hammer"))
    logging.info(l.parse("make 20 Dollars"))

    logging.info(await execute(world, jacob, l.parse("make My Beer")))
    logging.info(await execute(world, jacob, l.parse("drop")))
    logging.info(await execute(world, jacob, l.parse("hold beer")))
    logging.info(await execute(world, jacob, l.parse("modify when drank")))
    logging.info(await execute(world, jacob, l.parse("modify name IPA")))
    logging.info(await execute(world, jacob, l.parse("modify alcohol 100")))
    logging.info(await execute(world, jacob, l.parse("look at ipa")))
    logging.info(await execute(world, jacob, l.parse("call this IPA")))
    logging.info(await execute(world, jacob, l.parse("drink ipa")))
    logging.info(await execute(world, jacob, l.parse("go door")))
    logging.info(await execute(world, jacob, l.parse("home")))
    logging.info(await execute(world, jacob, l.parse("look at myself")))
    logging.info(await execute(world, jacob, l.parse("kiss carla")))
    logging.info(await execute(world, jacob, l.parse("kick carla")))
    logging.info(await execute(world, jacob, l.parse("heal carla")))
    logging.info(await execute(world, jacob, l.parse("hug carla")))
    logging.info(await execute(world, jacob, l.parse("make ipa")))
    logging.info(await execute(world, jacob, l.parse("forget ipa")))
    logging.info(await execute(world, jacob, l.parse("auth asdfasdf")))
    logging.info(await execute(world, jacob, l.parse("make 20 Dollars")))

    logging.info(world.look(jacob))


async def test_behavior():
    bus = game.EventBus()
    world = game.World(bus)
    carla = game.Player(owner=world, details=props.Details("Carla"))
    jacob = game.Player(owner=world, details=props.Details("Jacob"))
    hammer = game.Item(owner=jacob, details=props.Details("Hammer"))
    world.add_area(
        game.Area(owner=jacob, details=props.Details("Living room")).add_item(hammer)
    )
    world.add_area(game.Area(owner=jacob, details=props.Details("Kitchen")))
    await world.perform(jacob, actions.Join())
    await world.perform(carla, actions.Join())

    hammer.add_behavior(
        "b:test:drop:after",
        lua="""
function(s, world, player)
    if not player.gold then
        player.gold = { total = 0 }
    end
    if player.gold.total < 1 then
        player.gold.total = player.gold.total + 1
    else
        debug("yes!")
    end
    debug("ok")
end
""",
    )

    print(hammer.behaviors)

    logging.info(await execute(world, jacob, l.parse("hold hammer")))
    logging.info(await execute(world, jacob, l.parse("drop")))
    logging.info(await execute(world, jacob, l.parse("hold hammer")))
    logging.info(await execute(world, jacob, l.parse("drop")))

    logging.info(jacob.details)

    db = SqlitePersistence()
    await db.open("test.sqlite3")
    await db.save(world)

    crypto.test()


if __name__ == "__main__":
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    print()
    logging.info("testing:basic")
    asyncio.run(test_run())
    print()
    logging.info("testing:behavior")
    asyncio.run(test_behavior())
