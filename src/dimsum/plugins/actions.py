import logging
import lark

import model.entity as entity
import model.world as world
import model.game as game
import model.finders as finders
import model.reply as reply

import context

import model.scopes.movement as movement

log = logging.getLogger("dimsum.plugins")


class PersonAction(game.Action):
    async def perform(
        self,
        world: world.World,
        area: entity.Entity,
        person: entity.Entity,
        ctx: context.Ctx,
        **kwargs
    ):
        raise NotImplementedError


class Unknown(PersonAction):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def perform(
        self,
        world: world.World,
        area: entity.Entity,
        person: entity.Entity,
        ctx: context.Ctx,
        **kwargs
    ):
        log.warning("{0} performed".format(self))
        return reply.Failure("sorry, i don't understand")


class BaseEvaluator(lark.Transformer):
    def __init__(self, world: world.World, player: entity.Entity):
        self.world = world
        self.player = player

    def start(self, args):
        return args[0]

    def verbs(self, args):
        return args[0]

    def quoted_string(self, args):
        return args[0][1:-1]

    def string(self, args):
        return args[0]

    def text(self, args):
        return str(args[0])

    def number(self, args):
        return float(args[0])

    def noun(self, args):
        return args[0]

    def this(self, args):
        return finders.AnyHeldItem()

    def direction(self, args):
        for d in movement.Direction:
            if str(args[0]).lower() == d.name.lower():
                return d
        raise Exception("unknown movement.Direction")

    def general_noun(self, args):
        return finders.AnyItem(str(args[0]))

    def object_by_gid(self, args):
        return finders.ObjectNumber(int(args[0]))

    # Would love to move these closer to creation.
    def makeable_noun(self, args):
        return finders.MaybeItemOrRecipe(str(args[0]))

    def makeable(self, args):
        return args[0]
