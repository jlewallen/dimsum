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

    world.add_area(Area(owner=jacob, details=Details("Living room")).add_item(hammer))
    world.add_area(Area(owner=jacob, details=Details("Kitchen")))
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
    await world.drop(jacob)

    idea = Item(owner=jacob, details=Details("Idea", "It's genius."))
    await world.make(jacob, idea)
    await world.modify(jacob, "name Good Idea")
    await world.modify(jacob, "desc These are very rare.")
    logging.info(world.look(jacob))
    await world.drop(jacob)

    door = Item(owner=jacob, details=Details("Door", "It's wooden."))
    await world.make(jacob, door)
    await world.go(jacob, "Door")
    logging.info(world.look(jacob))
    await world.modify(jacob, "name An office.")
    await world.modify(
        jacob,
        "desc This is a lovely room, more garden than room. The walls are barely visible through the potted plants and vines.",
    )
    logging.info(world.look(jacob))
    await world.go(jacob, "Door")
    logging.info(world.look(jacob))

    logging.info("saving and reloading")

    db = SqlitePersistence()

    await db.open("test.sqlite3")
    await db.save(world)
    restored = World(bus)
    await db.load(restored)
    logging.info(restored.look(restored.players()[0]))


if __name__ == "__main__":
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    asyncio.run(test_run())
