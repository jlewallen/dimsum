import logging
import sys

from persistence import *
from game import *


async def test_run():
    bus = EventBus()
    world = World(bus)

    jacob = Player(owner=world, details=Details("Jacob", "Curly haired bastard."))
    carla = Player(owner=world, details=Details("Carla", "Chief salad officer."))
    hammer = Item(owner=jacob, details=Details("Hammer", "It's heavy."))

    await world.add_area(
        Area(owner=jacob, details=Details("Living room")).add_item(hammer)
    )
    await world.add_area(Area(owner=jacob, details=Details("Kitchen")))
    await world.join(jacob)
    await world.join(carla)

    logging.info(world.look(jacob))
    logging.info(world.look(carla))

    await world.hold(jacob, "hammer")

    logging.info(world.look(jacob))
    logging.info(world.look(carla))

    await world.give(jacob, "carla", "hammer")

    trampoline = Item(owner=jacob, details=Details("Trampoline", "It's bouncy."))

    await world.make(jacob, trampoline)
    await world.drop(jacob)
    await world.hold(jacob, "trampoline")

    idea = Item(owner=jacob, details=Details("Idea", "It's genius."))

    await world.make(jacob, idea)
    await world.drop(jacob)

    db = SqlitePersistence()

    await db.open("test.sqlite3")
    await db.save(world)

    restored = World(bus)
    await db.load(restored)
    logging.info(restored.look(restored.players()[0]))


if __name__ == "__main__":
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    asyncio.run(test_run())
