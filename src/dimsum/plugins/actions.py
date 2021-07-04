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


class Unknown(PersonAction):
    async def perform(self, **kwargs):
        log = logging.getLogger("dimsum.unknown")
        log.warning("{0} performed".format(self))
        return game.Failure("sorry, i don't understand")
