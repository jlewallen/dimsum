import logging

import model.entity as entity
import model.world as world
import model.game as game

import context


class PersonAction(game.Action):
    async def perform(
        self,
        world: world.World,
        area: entity.Entity,
        person: entity.Entity,
        ctx: context.Ctx,
        **kwargs
    ) -> game.Reply:
        raise NotImplementedError
