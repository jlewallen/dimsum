import logging
from typing import Type, Optional

from context import Ctx
from model.game import *
from model.reply import *
from model.world import *
from model.finders import *
from model.things import *
import model.scopes.users as users
from plugins.actions import *
import grammars
import transformers

log = logging.getLogger("dimsum")


class Auth(PersonAction):
    def __init__(self, password=None, **kwargs):
        super().__init__(**kwargs)
        self.password = password

    async def perform(
        self,
        world: World,
        area: entity.Entity,
        person: entity.Entity,
        ctx: Ctx,
        **kwargs
    ):
        with person.make(users.Auth) as auth:
            auth.change(self.password)
            log.info(auth.password)
        return Success("done, https://mud.espial.me")


class Freeze(PersonAction):
    def __init__(self, item: Optional[ItemFinder] = None, **kwargs):
        super().__init__(**kwargs)
        assert item
        self.item = item

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
        self,
        world: World,
        area: entity.Entity,
        person: entity.Entity,
        ctx: Ctx,
        **kwargs
    ):
        item = await world.apply_item_finder(person, self.item)
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
        start:             auth | freeze | unfreeze

        auth:              "auth" TEXT
        freeze:            "freeze" held                           -> freeze
        unfreeze:          "unfreeze" held                         -> unfreeze
"""
