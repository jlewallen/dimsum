from typing import Any, List, Type

import logging

import model.properties as properties
import model.scopes.occupyable as occupyable

import grammars

from model.entity import *
from model.events import *
from model.world import *
from model.reply import *

from plugins.actions import *
from context import *

log = logging.getLogger("dimsum")


class PlayerSpoke(StandardEvent):
    pass


class PlayerTold(StandardEvent):
    @property
    def audience(self) -> Audience:
        return Audience.DIRECT


class Say(PersonAction):
    def __init__(self, message: str = None, **kwargs):
        super().__init__(**kwargs)
        assert message
        self.message = message

    async def perform(
        self, world: World, area: Entity, person: Entity, ctx: Ctx, **kwargs
    ):
        with area.make_and_discard(occupyable.Occupyable) as here:
            await ctx.publish(
                PlayerSpoke(
                    message=self.message, person=person, area=area, heard=here.occupied
                )
            )
        return Success()


class Tell(PersonAction):
    def __init__(self, message: str = None, **kwargs):
        super().__init__(**kwargs)
        assert message
        self.message = message

    async def perform(
        self, world: World, area: Entity, person: Entity, ctx: Ctx, **kwargs
    ):
        await ctx.publish(PlayerTold(person=person, area=area))
        return Success("told")


@grammars.grammar()
class Grammar(grammars.Grammar):
    @property
    def evaluator(self):
        return Evaluator

    @property
    def lark(self) -> str:
        return """
        start:             say | tell

        say:               ("say" | "\\"") TEXT
        tell:              "tell" noun TEXT
"""


class Evaluator(Evaluator):
    def say(self, args):
        return Say(str(args[0]))

    def tell(self, args):
        return Tell(args[0], str(args[1]))
