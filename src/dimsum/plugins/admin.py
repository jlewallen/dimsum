from typing import Type, Optional

import grammars
import transformers
import tools
from loggers import get_logger
from model import *
from finders import *
from plugins.actions import PersonAction
from datetime import datetime
import scopes.users as users

register_username = users.register_username
lookup_username = users.lookup_username

log = get_logger("dimsum")


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
        return Success("Done, https://mud.espial.me")


class Invite(PersonAction):
    def __init__(self, password=None, **kwargs):
        super().__init__(**kwargs)
        assert password
        self.password: str = password

    async def perform(
        self, world: World, area: Entity, person: Entity, ctx: Ctx, **kwargs
    ):
        with person.make_and_discard(users.Auth) as auth:
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
            return Failure("Freeze what?")

        if not item.can_modify():
            return Failure("Already frozen, pal.")

        if not item.freeze(person.identity):
            return Failure("You can't do that!")

        return Success("Frozen")


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
            return Failure("Unfreeze what?")

        if item.can_modify():
            return Failure("Why do that?")

        if not item.unfreeze(person.identity):
            return Failure("You can't do that! Is that yours?")

        return Success("Unfrozen!")


class SystemBackup(PersonAction):
    async def perform(
        self, world: World, area: Entity, person: Entity, ctx: Ctx, **kwargs
    ):
        # Easier to just violate norms and ask for forgiveness than come up with
        # an over-engineered solution to this one.
        now = datetime.now()
        info = tools.flatten(await ctx.session.store.backup(now))  # type:ignore
        return Success(f"Done: {info}")


class Transformer(transformers.Base):
    def auth(self, args):
        return Auth(password=str(args[0]))

    def invite(self, args):
        return Invite(password=str(args[0]))

    def freeze(self, args):
        return Freeze(item=args[0])

    def unfreeze(self, args):
        return Unfreeze(item=args[0])

    def system_backup(self, args):
        return SystemBackup()


@grammars.grammar()
class AdminGrammar(grammars.Grammar):
    @property
    def transformer_factory(self) -> Type[transformers.Base]:
        return Transformer

    @property
    def lark(self) -> str:
        return """
        start:             auth | invite | freeze | unfreeze | sys_backup

        auth:              "auth" TEXT
        invite:            "invite" TEXT
        freeze:            "freeze" held                           -> freeze
        unfreeze:          "unfreeze" held                         -> unfreeze
        sys_backup:        "sys" "backup"                          -> system_backup
"""
