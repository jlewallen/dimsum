import pytest

import model.game as game
import model.reply as reply
import model.health as health
import model.carryable as carryable

import test


@pytest.mark.asyncio
async def test_make_food():
    tw = test.TestWorld()
    await tw.initialize()
    await tw.success("make Steak")
    await tw.success("modify when eaten")
    await tw.success("modify protein 100")
    await tw.success("eat steak")
    assert len(tw.player.make(carryable.Containing).holding) == 0
    with tw.player.make(health.Health) as player:
        assert player.medical.nutrition.properties["protein"] == 100


@pytest.mark.asyncio
async def test_make_drinks():
    tw = test.TestWorld()
    await tw.initialize()
    await tw.success("make IPA")
    await tw.success("modify when drank")
    await tw.success("modify alcohol 100")
    await tw.success("drink ipa")
    assert len(tw.player.make(carryable.Containing).holding) == 0
    with tw.player.make(health.Health) as player:
        assert player.medical.nutrition.properties["alcohol"] == 100


@pytest.mark.asyncio
async def test_try_eat():
    tw = test.TestWorld()
    await tw.initialize()
    await tw.success("make IPA")
    await tw.failure("drink ipa")
    assert len(tw.player.make(carryable.Containing).holding) == 1


@pytest.mark.asyncio
async def test_try_drink():
    tw = test.TestWorld()
    await tw.initialize()
    await tw.success("make IPA")
    await tw.failure("drink ipa")
    assert len(tw.player.make(carryable.Containing).holding) == 1


@pytest.mark.asyncio
async def test_taking_multiple_bites():
    tw = test.TestWorld()
    await tw.initialize()
    await tw.success("make Cake")
    await tw.success("modify when eaten")
    await tw.success("modify servings 2")
    await tw.success("eat cake")
    assert len(tw.player.make(carryable.Containing).holding) == 1
    await tw.success("eat cake")
    assert len(tw.player.make(carryable.Containing).holding) == 0


@pytest.mark.asyncio
async def test_taking_multiple_sips():
    tw = test.TestWorld()
    await tw.initialize()
    await tw.success("make IPA")
    await tw.success("modify when drank")
    await tw.success("modify alcohol 100")
    await tw.success("modify servings 2")
    await tw.success("drink ipa")
    assert len(tw.player.make(carryable.Containing).holding) == 1
    await tw.success("drink ipa")
    assert len(tw.player.make(carryable.Containing).holding) == 0


@pytest.mark.asyncio
@pytest.mark.skip(reason="todo")
async def test_modifying_servings_on_unedible_things():
    pass
