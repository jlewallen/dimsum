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

DefaultBody = """
# Default Help Page

This is a brand new help page that you can edit by using `edit
help`.

First, a brief introduction to the syntax used in this particular help
system, other systems may adopt their own style as all of these are
edited live.

One of the first things you should know is that you can also
edit the help associated with anything in the world by using:

```
edit help box
```

Where, in this case box uniquely identifies something nearby with box
in its name. You can use as much as needed to specify the thing you'd
like to make changes to uniquely, just as you do when interacting with
the object in other ways.
"""


class EncyclopediaClass(scopes.ItemClass):
    pass


class Encyclopedia(Scope):
    def __init__(self, body: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        self.body = body if body else DefaultBody


class ReadHelp(PersonAction):
    def __init__(
        self,
        query: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.query = query

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
        with entity.make(Encyclopedia) as pedia:
            return Help(pedia.body)


@event
@dataclasses.dataclass(frozen=True)
class EditingEntityHelp(StandardEvent):
    entity: Entity
    interactive: bool = True


class EditEntity(PersonAction):
    def __init__(self, item: Optional[ItemFinder] = None, **kwargs):
        super().__init__(**kwargs)
        self.item = item

    async def perform(
        self, world: World, area: Entity, person: Entity, ctx: Ctx, **kwargs
    ):
        entity = await materialize_well_known_entity(
            world,
            ctx,
            EncyclopediaKey,
            create_args=dict(props=Common("Encyclopedia"), klass=EncyclopediaClass),
        )
        with entity.make(Encyclopedia) as pedia:
            pass
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
        WIKI_WORD:              /[A-Z]+[a-zA-Z0-9]*/
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
            return EditEntity(args[0])
        return EditEntity(None)

    def help_create(self, args):
        log.info("help-create-args: %s", args)
        return ReadHelp(str(args[0]), create=True)

    def help_page(self, args):
        return args[0]
