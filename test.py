import logging
import sys

from persistence import *
from game import *


async def test_run():
    bus = EventBus()
    world = World(bus)

    jacob = Player(world, Details("Jacob", "Curly haired bastard."))
    carla = Player(world, Details("Carla", "Chief salad officer."))
    hammer = Item(jacob, Details("Hammer", "It's heavy."))

    await world.add_area(Area(jacob, Details("Living room")).add_item(hammer))
    await world.add_area(Area(jacob, Details("Kitchen")))
    await world.join(jacob)
    await world.join(carla)

    logging.info(world.look(jacob))
    logging.info(world.look(carla))

    await world.hold(jacob, "hammer")

    logging.info(world.look(jacob))
    logging.info(world.look(carla))

    await world.give(jacob, "carla", "hammer")

    trampoline = Item(jacob, Details("Trampoline", "It's bouncy."))

    await world.make(jacob, trampoline)
    await world.drop(jacob)
    await world.hold(jacob, "trampoline")

    idea = Item(jacob, Details("Idea", "It's genius."))

    await world.make(jacob, idea)
    await world.drop(jacob)

    db = SqlitePersistence()

    await db.open()
    await db.save(world)

    restored = World(bus)
    await db.load(restored)
    logging.info(restored.look(restored.players[0]))


if __name__ == "__main__":
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    asyncio.run(test_run())
