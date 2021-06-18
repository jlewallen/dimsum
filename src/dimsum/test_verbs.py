import sys
import logging
import pytest

import context
import properties
import game
import things
import entity
import world

import test


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
