import pytest
import logging

import entity
import game
import things
import world
import reply
import serializing
import persistence
import health
import mechanics
import test
import carryable

import ownership

log = logging.getLogger("dimsum")


@pytest.mark.asyncio
async def test_simple_action_verbs():
    tw = test.TestWorld()
    await tw.initialize()
    await tw.add_carla()
    for verb in ["kiss", "heal", "hug", "tickle", "poke"]:
        await tw.success(verb + " carla")
    with tw.player.make(carryable.Containing) as pockets:
        assert len(pockets.holding) == 0


@pytest.mark.asyncio
async def test_world_owns_itself(caplog):
    whatever = test.create_empty_world()
    with whatever.make(ownership.Ownership) as props:
        assert isinstance(props.owner, world.World)


@pytest.mark.asyncio
async def test_obliterate():
    tw = test.TestWorld()
    await tw.initialize()
    await tw.success("make Hammer")
    with tw.player.make(carryable.Containing) as pockets:
        assert len(pockets.holding) == 1
        await tw.success("obliterate")
        assert len(pockets.holding) == 0


@pytest.mark.asyncio
async def test_obliterate_separate_transactions():
    tw = test.TestWorld()
    await tw.initialize()
    await tw.success("make Hammer")
    with tw.player.make(carryable.Containing) as pockets:
        assert len(pockets.holding) == 1
    await tw.success("obliterate")
    with tw.player.make(carryable.Containing) as pockets:
        assert len(pockets.holding) == 0


@pytest.mark.asyncio
async def test_recipe_simple():
    tw = test.TestWorld()
    await tw.initialize()
    await tw.success("make IPA")
    await tw.success("modify alcohol 100")
    with tw.player.make(carryable.Containing) as pockets:
        with pockets.holding[0].make(health.Edible) as edible:
            assert edible.nutrition.properties["alcohol"] == 100

    assert len(tw.player.make(mechanics.Memory).memory.keys()) == 0
    await tw.success("call this Fancy IPA")
    assert len(tw.player.make(mechanics.Memory).memory.keys()) == 1

    await tw.success("make fancy")
    with tw.player.make(carryable.Containing) as pockets:
        assert len(pockets.holding) == 1


@pytest.mark.asyncio
async def test_freezing_simple():
    tw = test.TestWorld()
    await tw.initialize()
    await tw.success("make Box")
    with tw.player.make(carryable.Containing) as pockets:
        assert len(pockets.holding) == 1
    await tw.failure("unfreeze box")
    await tw.success("freeze box")
    await tw.failure("modify name Ignored Box")
    await tw.success("unfreeze box")
    await tw.success("modify name New Box")


@pytest.mark.asyncio
async def test_freezing_others_unable_unfreeze():
    tw = test.TestWorld()
    await tw.initialize()
    await tw.add_carla()
    await tw.success("make Box")
    with tw.player.make(carryable.Containing) as pockets:
        assert len(pockets.holding) == 1
    await tw.failure("unfreeze box")
    await tw.success("freeze box")
    await tw.success("drop")
    await tw.success("hold box", person=tw.carla)
    await tw.failure("modify name Ignored Box")
    await tw.failure("unfreeze box")


@pytest.mark.asyncio
async def test_lookup_by_object_number():
    tw = test.TestWorld()
    await tw.initialize()
    await tw.failure("freeze #3")
    await tw.success("make Box")
    await tw.success("freeze #3")
