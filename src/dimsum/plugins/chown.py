import dataclasses
from typing import Type, Optional, List, Dict, Any

import grammars
import transformers
from loggers import get_logger
from model import *
from finders import *
from plugins.actions import PersonAction
import scopes.users as users
import scopes.ownership as ownership

log = get_logger("dimsum.plugins.chown")


class Chown(PersonAction):
    def __init__(
        self,
        item: Optional[ItemFinder] = None,
        who: Optional[ItemFinder] = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        assert item
        self.item = item
        assert who
        self.who = who

    async def perform(
        self, world: World, area: Entity, person: Entity, ctx: Ctx, **kwargs
    ):
        item = await ctx.apply_item_finder(person, self.item)
        if not item:
            return Failure("chown what?")

        who = await ctx.apply_item_finder(person, self.who)
        if not who:
            return Failure("Who?")

        ownership.set_owner(item, who)

        return Success("Done!")


class Transformer(transformers.Base):
    def chown_entity_self(self, args):
        return Chown(item=args[0], who=FindCurrentPerson())

    def chown_entity_somebody(self, args):
        return Chown(item=args[0], who=args[1])


@grammars.grammar()
class ChownGrammar(grammars.Grammar):
    @property
    def transformer_factory(self) -> Type[transformers.Base]:
        return Transformer

    @property
    def lark(self) -> str:
        return """
        start:             chown

        chown:             "chown" noun                 -> chown_entity_self
                         | "chown" noun noun            -> chown_entity_somebody
"""
