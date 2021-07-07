import test

import context
import model.entity as entity
import model.world as world
import pytest


class Verb:
    async def perform(
        self, ctx: context.Ctx, world: world.World, player: entity.Entity
    ):
        pass


class LuaVerb(Verb):
    async def perform(
        self, ctx: context.Ctx, world: world.World, player: entity.Entity
    ):
        pass


@pytest.mark.asyncio
async def test_verbs_whatever(caplog):
    tw = test.TestWorld()
    await tw.initialize()
