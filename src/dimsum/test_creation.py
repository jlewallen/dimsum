import logging
import test

import freezegun
import handlers
import model.properties as properties
import model.scopes as scopes
import model.scopes.behavior as behavior
import model.scopes.carryable as carryable
import model.visual as visual
import pytest

log = logging.getLogger("dimsum")


@pytest.mark.asyncio
@freezegun.freeze_time("2019-09-25")
async def test_create_thing(snapshot):
    with test.Deterministic():
        tw = test.TestWorld(handlers=[handlers.create(visual.NoopComms())])
        await tw.initialize()
        await tw.success("create thing Box")
        snapshot.assert_match(await tw.to_json(), "world.json")


@pytest.mark.asyncio
@freezegun.freeze_time("2019-09-25")
async def test_create_area(snapshot):
    with test.Deterministic():
        tw = test.TestWorld(handlers=[handlers.create(visual.NoopComms())])
        await tw.initialize()
        await tw.success("create area Treehouse")
        snapshot.assert_match(await tw.to_json(), "world.json")


@pytest.mark.asyncio
@freezegun.freeze_time("2019-09-25")
async def test_create_exit(snapshot):
    with test.Deterministic():
        tw = test.TestWorld(handlers=[handlers.create(visual.NoopComms())])
        await tw.initialize()
        await tw.success("create exit Window")
        snapshot.assert_match(await tw.to_json(), "world.json")


@pytest.mark.asyncio
async def test_obliterate():
    tw = test.TestWorld()
    await tw.initialize()
    await tw.success("make Hammer")

    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        with jacob.make(carryable.Containing) as pockets:
            assert len(pockets.holding) == 1

    await tw.success("obliterate")

    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        with jacob.make(carryable.Containing) as pockets:
            assert len(pockets.holding) == 0


@pytest.mark.asyncio
async def test_obliterate_thing_with_behavior():
    tw = test.TestWorld()
    await tw.initialize()

    with tw.domain.session() as session:
        world = await session.prepare()

        hammer = tw.add_item_to_welcome_area(
            scopes.item(creator=world, props=properties.Common("Hammer")),
            session=session,
        )

        with hammer.make(behavior.Behaviors) as behave:
            behave.add_behavior(
                world,
                python="#",
            )

        await session.save()

    await tw.success("hold hammer")
    await tw.success("obliterate")

    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        with jacob.make(carryable.Containing) as pockets:
            assert len(pockets.holding) == 0

    await tw.success("look")
