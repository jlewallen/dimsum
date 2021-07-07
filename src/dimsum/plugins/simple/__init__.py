from typing import Any, List, Type, Optional

import logging

import model.properties as properties
import model.finders as finders
import model.entity as entity

import grammars
import transformers

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
        return Success("you swung %s" % (item))


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
        return Success("you hit %s" % (item))


@grammars.grammar()
class Grammar(grammars.Grammar):
    @property
    def transformer_factory(self) -> Type[transformers.Base]:
        return Transformer

    @property
    def lark(self) -> str:
        return """
        start:             plant | swing | heal | hug | kiss | kick | tickle | poke | hit

        plant:             "plant" (noun)?
        swing:             "swing" noun
        heal:              "heal" noun
        hug:               "hug" noun
        kiss:              "kiss" noun
        kick:              "kick" noun
        tickle:            "tickle" noun ("with" noun)?
        poke:              "poke" noun ("with" noun)?
        hit:               "hit" noun ("with" noun)?
"""


class Transformer(transformers.Base):
    def plant(self, args):
        return Plant(item=args[0])

    def swing(self, args):
        return Swing(item=args[0])

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
