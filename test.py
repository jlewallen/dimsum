import logging
import sys
import lupa

from persistence import *
from game import *
from grammar import *
from evaluator import *

from lark import Tree, Transformer


async def test_run():
    bus = EventBus()
    world = World(bus)

    jacob = Player(owner=world, details=Details("Jacob", "Curly haired bastard."))
    carla = Player(owner=world, details=Details("Carla", "Chief salad officer."))
    hammer = Item(owner=jacob, details=Details("Hammer", "It's heavy."))

    world.add_area(Area(owner=jacob, details=Details("Living room")).add_item(hammer))
    world.add_area(Area(owner=jacob, details=Details("Kitchen")))
    await world.perform(jacob, game.Join())
    await world.perform(carla, game.Join())

    logging.info(world.look(jacob))
    logging.info(world.look(carla))

    await world.perform(jacob, game.Hold(item=hammer))

    logging.info(world.look(jacob))
    logging.info(world.look(carla))

    trampoline = Item(owner=jacob, details=Details("Trampoline", "It's bouncy."))

    await world.perform(jacob, game.Make(trampoline))
    await world.perform(jacob, game.Drop())
    await world.perform(jacob, game.Hold(item=trampoline))
    await world.perform(jacob, game.Drop())

    idea = Item(owner=jacob, details=Details("Idea", "It's genius."))
    await world.perform(jacob, game.Make(idea))
    logging.info(world.look(jacob))
    await world.perform(jacob, game.Drop())

    door = Item(owner=jacob, details=Details("Door", "It's wooden."))
    await world.perform(jacob, game.Make(door))
    await world.perform(jacob, game.Go(item=door))
    logging.info(world.look(jacob))
    await world.perform(jacob, game.Go(item=door))
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

    async def execute(world, player, tree):
        action = create(world, player).transform(tree)
        if action:
            return await world.perform(player, action)
        return None

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
    logging.info(world.look(jacob))


class Behavior(game.PropertyMap):
    def execute(self, name):
        pass

async def test_lua():
    lua = lupa.LuaRuntime(unpack_returned_tuples=True)
    logging.info(lua.eval('1+1'))

    func = lua.eval('function(f, n) return f(n) end')
    logging.info(lupa.lua_type(func))

    bus = EventBus()
    world = World(bus)
    jacob = Player(owner=world, details=Details("Jacob", "Curly haired bastard."))

    lua.globals().world = world
    lua.globals().player = jacob

    logging.info(lua.eval('player'))
    logging.info(lua.eval('world'))

    b = Behavior()

if __name__ == "__main__":
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    logging.info("testing:basic")
    asyncio.run(test_run())
    logging.info("testing:lua")
    asyncio.run(test_lua())
