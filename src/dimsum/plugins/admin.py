import logging
from typing import Type, Optional

import grammars
import transformers
from model import *
from finders import *
from plugins.actions import PersonAction
import scopes.users as users

log = logging.getLogger("dimsum")


class Auth(PersonAction):
    def __init__(self, password=None, **kwargs):
        super().__init__(**kwargs)
        assert password
        self.password: str = password

    async def perform(
        self, world: World, area: Entity, person: Entity, ctx: Ctx, **kwargs
    ):
        with person.make(users.Auth) as auth:
            auth.change(self.password)
        return Success("done, https://mud.espial.me")


class Invite(PersonAction):
    def __init__(self, password=None, **kwargs):
        super().__init__(**kwargs)
        assert password
        self.password: str = password

    async def perform(
        self, world: World, area: Entity, person: Entity, ctx: Ctx, **kwargs
    ):
        with person.make(users.Auth) as auth:
            url, token = auth.invite(self.password)
            return Universal(
                "All good to go! The new URL is %(url)s", url=url, token=token
            )


class Freeze(PersonAction):
    def __init__(self, item: Optional[ItemFinder] = None, **kwargs):
        super().__init__(**kwargs)
        assert item
        self.item = item

    async def perform(
        self, world: World, area: Entity, person: Entity, ctx: Ctx, **kwargs
    ):
        item = await ctx.apply_item_finder(person, self.item)
        if not item:
            return Failure("freeze what?")

        if not item.can_modify():
            return Failure("already frozen, pal")

        if not item.freeze(person.identity):
            return Failure("you can't do that!")

        return Success("frozen")


class Unfreeze(PersonAction):
    def __init__(self, item: Optional[ItemFinder] = None, **kwargs):
        super().__init__(**kwargs)
        assert item
        self.item = item

    async def perform(
        self, world: World, area: Entity, person: Entity, ctx: Ctx, **kwargs
    ):
        item = await ctx.apply_item_finder(person, self.item)
        if not item:
            return Failure("unfreeze what?")

        if item.can_modify():
            return Failure("why do that?")

        if not item.unfreeze(person.identity):
            return Failure("you can't do that! is that yours?")

        return Success("unfrozen")


class Transformer(transformers.Base):
    def auth(self, args):
        return Auth(password=str(args[0]))

    def invite(self, args):
        return Invite(password=str(args[0]))

    def freeze(self, args):
        return Freeze(item=args[0])

    def unfreeze(self, args):
        return Unfreeze(item=args[0])


@grammars.grammar()
class AdminGrammar(grammars.Grammar):
    @property
    def transformer_factory(self) -> Type[transformers.Base]:
        return Transformer

    @property
    def lark(self) -> str:
        return """
        start:             auth | invite | freeze | unfreeze

        auth:              "auth" TEXT
        invite:            "invite" TEXT
        freeze:            "freeze" held                           -> freeze
        unfreeze:          "unfreeze" held                         -> unfreeze
"""
