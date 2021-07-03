from typing import Any, List, Type, Optional

import logging

import model.properties as properties
import model.finders as finders
import model.entity as entity

import grammars

from model.reply import *
from model.game import *
from model.things import *
from model.events import *
from model.world import *

from plugins.actions import *
from context import *

import model.scopes.movement as movement

log = logging.getLogger("dimsum")


class SimpleVerb(PersonAction):
    def __init__(self, who=None, item: Optional[ItemFinder] = None, **kwargs):
        super().__init__()
        self.who = who
        self.item = item if item else finders.FindNone()


class Plant(SimpleVerb):
    async def perform(
        self,
        world: World,
        area: entity.Entity,
        person: entity.Entity,
        ctx: Ctx,
        **kwargs
    ):
        if not self.item:
            return Failure("plant what?")
        await ctx.extend(plant=self.item).hook("plant")
        return Success("you planted %s" % (self.item))


class Swing(SimpleVerb):
    async def perform(
        self,
        world: World,
        area: entity.Entity,
        person: entity.Entity,
        ctx: Ctx,
        **kwargs
    ):
        item = await world.apply_item_finder(person, self.item)
        if self.item:
            return Failure("swing what?")
        await ctx.extend(swing=item).hook("swing")
        return Success("you swung %s" % (item))


class Shake(SimpleVerb):
    async def perform(
        self,
        world: World,
        area: entity.Entity,
        person: entity.Entity,
        ctx: Ctx,
        **kwargs
    ):
        item = await world.apply_item_finder(person, self.item)
        if not item:
            return Failure("shake what?")
        await ctx.extend(shake=item).hook("shake")
        return Success("you shook %s" % (item))


class Heal(SimpleVerb):
    async def perform(
        self,
        world: World,
        area: entity.Entity,
        person: entity.Entity,
        ctx: Ctx,
        **kwargs
    ):
        if not self.who:
            return Failure("who?")
        await ctx.extend(heal=self.who).hook("heal:after")
        return Success("you healed %s" % (self.who))


class Hug(SimpleVerb):
    async def perform(
        self,
        world: World,
        area: entity.Entity,
        person: entity.Entity,
        ctx: Ctx,
        **kwargs
    ):
        if not self.who:
            return Failure("who?")
        await ctx.extend(hug=self.who).hook("hug:after")
        return Success("you hugged %s" % (self.who))


class Kiss(SimpleVerb):
    async def perform(
        self,
        world: World,
        area: entity.Entity,
        person: entity.Entity,
        ctx: Ctx,
        **kwargs
    ):
        if not self.who:
            return Failure("who?")
        await ctx.extend(kiss=self.who).hook("kiss:after")
        return Success("you kissed %s" % (self.who))


class Kick(SimpleVerb):
    async def perform(
        self,
        world: World,
        area: entity.Entity,
        person: entity.Entity,
        ctx: Ctx,
        **kwargs
    ):
        item = await world.apply_item_finder(person, self.item)
        if not item:
            return Failure("what?")
        await ctx.extend(kick=item).hook("kick:after")
        return Success("you kicked %s" % (item))


class Tickle(SimpleVerb):
    async def perform(
        self,
        world: World,
        area: entity.Entity,
        person: entity.Entity,
        ctx: Ctx,
        **kwargs
    ):
        if not self.who:
            return Failure("who?")
        await ctx.extend(tickle=self.who).hook("tickle:after")
        return Success("you tickled %s" % (self.who))


class Poke(SimpleVerb):
    async def perform(
        self,
        world: World,
        area: entity.Entity,
        person: entity.Entity,
        ctx: Ctx,
        **kwargs
    ):
        if not self.who:
            return Failure("who?")
        await ctx.extend(poke=self.who).hook("poke:after")
        return Success("you poked %s" % (self.who))


class Hit(SimpleVerb):
    async def perform(
        self,
        world: World,
        area: entity.Entity,
        person: entity.Entity,
        ctx: Ctx,
        **kwargs
    ):
        item = await world.apply_item_finder(person, self.item)
        if not item:
            return Failure("hit what?")
        await ctx.extend(swing=item).hook("hit")
        return Success("you hit %s" % (item))


@grammars.grammar()
class Grammar(grammars.Grammar):
    @property
    def evaluator(self) -> Type[BaseEvaluator]:
        return Evaluator

    @property
    def lark(self) -> str:
        return """
        start:             plant | swing | shake | heal | hug | kiss | kick | tickle | poke | hit

        plant:             "plant" (noun)?
        swing:             "swing" noun
        shake:             "shake" noun
        heal:              "heal" noun
        hug:               "hug" noun
        kiss:              "kiss" noun
        kick:              "kick" noun
        tickle:            "tickle" noun ("with" noun)?
        poke:              "poke" noun ("with" noun)?
        hit:               "hit" noun ("with" noun)?
"""


class Evaluator(BaseEvaluator):
    def plant(self, args):
        return actions.Plant(item=args[0])

    def swing(self, args):
        return Swing(item=args[0])

    def shake(self, args):
        return Shake(item=args[0])

    def heal(self, args):
        return Heal(who=args[0])

    def hug(self, args):
        return Hug(who=args[0])

    def kiss(self, args):
        return Kiss(who=args[0])

    def kick(self, args):
        return Kick(item=args[0])

    def tickle(self, args):
        return Tickle(who=args[0])

    def poke(self, args):
        return Poke(who=args[0])

    def hit(self, args):
        return Hit(item=args[0])
