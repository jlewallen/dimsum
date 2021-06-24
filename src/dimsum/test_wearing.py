import pytest

import test

import model.game as game
import model.reply as reply

import model.scopes.apparel as apparel
import model.scopes.carryable as carryable


@pytest.mark.asyncio
async def test_wearing_when_unwearable():
    tw = test.TestWorld()
    await tw.initialize()
    await tw.success("make Shoes")
    await tw.failure("wear shoes")

    with tw.domain.session() as session:
        jacob = await session.materialize(key=tw.jacob_key)
        assert len(jacob.make(carryable.Containing).holding) == 1
        assert len(jacob.make(apparel.Apparel).wearing) == 0


@pytest.mark.asyncio
async def test_simple_wear_and_remove():
    tw = test.TestWorld()
    await tw.initialize()
    await tw.success("make Shoes")
    await tw.success("modify when worn")
    await tw.success("wear shoes")

    with tw.domain.session() as session:
        jacob = await session.materialize(key=tw.jacob_key)
        assert len(jacob.make(carryable.Containing).holding) == 0
        assert len(jacob.make(apparel.Apparel).wearing) == 1

    await tw.success("remove shoes")

    with tw.domain.session() as session:
        jacob = await session.materialize(key=tw.jacob_key)
        assert len(jacob.make(carryable.Containing).holding) == 1
        assert len(jacob.make(apparel.Apparel).wearing) == 0
