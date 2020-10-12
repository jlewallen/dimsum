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
    await world.perform(jacob, game.Join())
    await world.perform(carla, game.Join())

    logging.info(world.look(jacob))
    logging.info(world.look(carla))

    await world.perform(jacob, game.Hold("hammer"))

    logging.info(world.look(jacob))
    logging.info(world.look(carla))

    trampoline = Item(owner=jacob, details=Details("Trampoline", "It's bouncy."))

    await world.perform(jacob, game.Make(trampoline))
    await world.perform(jacob, game.Drop())
    await world.perform(jacob, game.Hold("trampoline"))
    await world.perform(jacob, game.Drop())

    idea = Item(owner=jacob, details=Details("Idea", "It's genius."))
    await world.perform(jacob, game.Make(idea))
    await world.perform(jacob, game.Modify("name Good Idea"))
    await world.perform(jacob, game.Modify("desc These are very rare."))
    logging.info(world.look(jacob))
    await world.perform(jacob, game.Drop())

    door = Item(owner=jacob, details=Details("Door", "It's wooden."))
    await world.perform(jacob, game.Make(door))
    await world.perform(jacob, game.Go("door"))
    logging.info(world.look(jacob))
    await world.perform(jacob, game.Modify("name An office."))
    await world.perform(
        jacob,
        game.Modify(
            "desc This is a lovely room, more garden than room. The walls are barely visible through the potted plants and vines."
        ),
    )
    logging.info(world.look(jacob))
    await world.perform(jacob, game.Go("Door"))
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
