import test

import model.scopes.carryable as carryable
import model.scopes.health as health
import pytest


@pytest.mark.asyncio
async def test_make_food():
    tw = test.TestWorld()
    await tw.initialize()
    await tw.success("make Steak")
    await tw.success("modify when eaten")
    await tw.success("modify protein 100")
    await tw.success("eat steak")

    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        assert len(jacob.make(carryable.Containing).holding) == 0
        with jacob.make(health.Health) as player:
            assert player.medical.nutrition.properties["protein"] == 100


@pytest.mark.asyncio
async def test_make_drinks():
    tw = test.TestWorld()
    await tw.initialize()
    await tw.success("make IPA")
    await tw.success("modify when drank")
    await tw.success("modify alcohol 100")
    await tw.success("drink ipa")

    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        assert len(jacob.make(carryable.Containing).holding) == 0
        with jacob.make(health.Health) as player:
            assert player.medical.nutrition.properties["alcohol"] == 100


@pytest.mark.asyncio
async def test_try_eat():
    tw = test.TestWorld()
    await tw.initialize()
    await tw.success("make IPA")
    await tw.failure("drink ipa")

    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        assert len(jacob.make(carryable.Containing).holding) == 1


@pytest.mark.asyncio
async def test_try_drink():
    tw = test.TestWorld()
    await tw.initialize()
    await tw.success("make IPA")
    await tw.failure("drink ipa")

    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        assert len(jacob.make(carryable.Containing).holding) == 1


@pytest.mark.asyncio
async def test_taking_multiple_bites():
    tw = test.TestWorld()
    await tw.initialize()
    await tw.success("make Cake")
    await tw.success("modify when eaten")
    await tw.success("modify servings 2")
    await tw.success("eat cake")

    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        assert len(jacob.make(carryable.Containing).holding) == 1

    await tw.success("eat cake")

    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        assert len(jacob.make(carryable.Containing).holding) == 0


@pytest.mark.asyncio
async def test_taking_multiple_sips():
    tw = test.TestWorld()
    await tw.initialize()
    await tw.success("make IPA")
    await tw.success("modify when drank")
    await tw.success("modify alcohol 100")
    await tw.success("modify servings 2")
    await tw.success("drink ipa")

    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        assert len(jacob.make(carryable.Containing).holding) == 1

    await tw.success("drink ipa")

    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        assert len(jacob.make(carryable.Containing).holding) == 0


@pytest.mark.asyncio
@pytest.mark.skip(reason="todo")
async def test_modifying_servings_on_unedible_things():
    pass
