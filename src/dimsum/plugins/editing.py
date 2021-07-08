import dataclasses
import logging
from typing import Optional, Type

from context import *
import grammars
from model.entity import *
from model.events import *
from model.game import *
from model.reply import *
from model.world import *
from finders import *
from plugins.actions import *
import transformers

log = logging.getLogger("dimsum")


@event
@dataclasses.dataclass(frozen=True)
class EditingEntity(StandardEvent):
    entity: Entity
    interactive: bool = True


@dataclasses.dataclass(frozen=True)
class ScreenCleared(Reply):
    pass


class EditEntity(PersonAction):
    def __init__(self, item: Optional[ItemFinder] = None, **kwargs):
        super().__init__(**kwargs)
        assert item
        self.item = item

    async def perform(
        self, world: World, area: Entity, person: Entity, ctx: Ctx, **kwargs
    ):
        item = await world.apply_item_finder(person, self.item)
        if item:
            return EditingEntity(living=person, area=area, heard=[], entity=item)
        return Failure("where's that?")


class ClearScreen(PersonAction):
    async def perform(
        self, world: World, area: Entity, person: Entity, ctx: Ctx, **kwargs
    ):
        return ScreenCleared()


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
        start:             edit_entity | clear_screen

        edit_entity:       ("edit" | "ed") (here | this | noun)
        here:              "here"
        clear_screen:      "cls"
"""


class Transformer(transformers.Base):
    def here(self, args):
        return CurrentArea()

    def edit_entity(self, args):
        return EditEntity(args[0])

    def clear_screen(self, args):
        return ClearScreen()
