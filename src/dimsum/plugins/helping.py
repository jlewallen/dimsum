import copy
import dataclasses
import logging
from typing import Dict, List, Optional, Type

import grammars
import transformers
from model import *
from finders import *
from tools import *
from domains import Session
import scopes
from plugins.actions import PersonAction

log = logging.getLogger("dimsum")


@dataclasses.dataclass
class Help(Reply):
    body: str


EncyclopediaKey = "encyclopedia"


def _get_default_body(name: Optional[str]):
    return f"""
f'# {name or "WelcomePage"}'

This is your brand new help page that you can edit by using `edit help`.

Enjoy!
"""


class EncyclopediaClass(scopes.ItemClass):
    pass


class Encyclopedia(Scope):
    def __init__(self, body: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        self.acls: Acls = Acls.owner_writes()
        self.body: str = body if body else ""


class WriteHelp(PersonAction):
    def __init__(
        self,
        page_name: Optional[str] = None,
        page_body: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.page_name = page_name
        self.page_body = page_body

    async def perform(
        self,
        world: World,
        area: Entity,
        person: Entity,
        ctx: Ctx,
        **kwargs,
    ):
        entity = await materialize_well_known_entity(
            world,
            ctx,
            EncyclopediaKey,
            create_args=dict(props=Common("Encyclopedia"), klass=EncyclopediaClass),
        )
        if self.page_name:
            entity = await materialize_well_known_entity(
                entity,
                ctx,
                self.page_name,
                create_args=dict(props=Common(self.page_name), klass=EncyclopediaClass),
            )
        log.info("have %s", entity)
        with entity.make(Encyclopedia) as pedia:
            pedia.body = self.page_body
            entity.touch()
            assert pedia.body
            return Help(pedia.body)


class ReadHelp(PersonAction):
    def __init__(
        self,
        page_name: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.page_name = page_name

    async def perform(
        self,
        world: World,
        area: Entity,
        person: Entity,
        ctx: Ctx,
        **kwargs,
    ):
        entity = await materialize_well_known_entity(
            world,
            ctx,
            EncyclopediaKey,
            create_args=dict(props=Common("Encyclopedia"), klass=EncyclopediaClass),
        )
        if self.page_name:
            entity = await materialize_well_known_entity(
                entity,
                ctx,
                self.page_name,
                create_args=dict(props=Common(self.page_name), klass=EncyclopediaClass),
            )
        log.info("have %s", entity)
        with entity.make(Encyclopedia) as pedia:
            if pedia.body == "":
                pedia.body = _get_default_body(self.page_name)
            return Help(pedia.body)


@event
@dataclasses.dataclass(frozen=True)
class EditingEntityHelp(StandardEvent):
    entity: Entity
    interactive: bool = True


class EditHelp(PersonAction):
    def __init__(self, page_name: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        self.page_name = page_name

    async def perform(
        self, world: World, area: Entity, person: Entity, ctx: Ctx, **kwargs
    ):
        entity = await materialize_well_known_entity(
            world,
            ctx,
            EncyclopediaKey,
            create_args=dict(props=Common("Encyclopedia"), klass=EncyclopediaClass),
        )
        if self.page_name:
            entity = await materialize_well_known_entity(
                entity,
                ctx,
                self.page_name,
                create_args=dict(props=Common(self.page_name), klass=EncyclopediaClass),
            )
        with entity.make(Encyclopedia) as pedia:
            if pedia.body == "":
                pedia.body = _get_default_body(self.page_name)
            return EditingEntityHelp(source=person, area=area, heard=[], entity=entity)


@grammars.grammar()
class Grammar(grammars.Grammar):
    @property
    def order(self) -> int:
        return grammars.HIGHEST

    @property
    def transformer_factory(self) -> Type[transformers.Base]:
        return Transformer

    @property
    def lark(self) -> str:
        return """
        start:                  help | edit_help

        help:                   "help" help_page?           -> help
                              | "help" help_page "create"   -> help_create

        edit_help:              "edit" "help" help_page?    -> edit_help

        help_page:              WIKI_WORD
        WIKI_WORD:              /[A-Z]+[a-z]+([A-Z]+[a-z]+)+/
"""


class Transformer(transformers.Base):
    def help(self, args):
        log.info("help-args: %s", args)
        if args:
            return ReadHelp(args[0])
        return ReadHelp(None)

    def edit_help(self, args):
        log.info("edit-help-args: %s", args)
        if args:
            return EditHelp(str(args[0]))
        return EditHelp(None)

    def help_create(self, args):
        log.info("help-create-args: %s", args)
        return ReadHelp(str(args[0]), create=True)

    def help_page(self, args):
        return args[0]
