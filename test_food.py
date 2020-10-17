import pytest

import game
import props
import test


@pytest.mark.asyncio
async def test_make_food():
    tw = test.TestWorld()
    await tw.initialize()
    await tw.execute("make Steak")
    await tw.execute("modify when eaten")
    await tw.execute("modify protein 100")
    r = await tw.execute("eat steak")
    assert isinstance(r, game.Success)
    assert len(tw.player.holding) == 0
    assert tw.player.details["protein"] == 100


@pytest.mark.asyncio
async def test_make_drinks():
    tw = test.TestWorld()
    await tw.initialize()
    await tw.execute("make IPA")
    await tw.execute("modify when drank")
    await tw.execute("modify alcohol 100")
    r = await tw.execute("drink ipa")
    assert isinstance(r, game.Success)
    assert len(tw.player.holding) == 0
    assert tw.player.details["alcohol"] == 100


@pytest.mark.asyncio
async def test_try_eat():
    tw = test.TestWorld()
    await tw.initialize()
    await tw.execute("make IPA")
    r = await tw.execute("drink ipa")
    assert isinstance(r, game.Failure)
    assert len(tw.player.holding) == 1


@pytest.mark.asyncio
async def test_try_drink():
    tw = test.TestWorld()
    await tw.initialize()
    await tw.execute("make IPA")
    r = await tw.execute("drink ipa")
    assert isinstance(r, game.Failure)
    assert len(tw.player.holding) == 1
