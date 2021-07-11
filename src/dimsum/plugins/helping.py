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

This is your brand new help page that you can edit by using `edit
help`.

First, it's important to know that the main way you interact with this
world is by typing things in. Simple English-like command from a
grammar that grows with your world. These are commands like:

```
look
hold box
drop
```

You may notice that we've styled that text differently, that's because
those are examples of things you can type in. Give it a try!

One thing that may stand out in the list above is that the `hold`
takes more words, in this case a noun to help locate the thing you'd
like to hold.

Feel free to explore this and the help system. Some other topics are:

* DesignPhilosophy
* CreatingThings
* MovingAround

For a good place to start learning how things work behind the scenes
you can try reading DesignPhilosophy.

Enjoy!
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
