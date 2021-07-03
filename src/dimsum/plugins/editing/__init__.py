from typing import Any, List, Type

import logging

import grammars

from model.entity import *
from model.world import *
from model.events import *
from model.things import *
from model.reply import *
from model.game import *

from plugins.actions import *
from context import *

log = logging.getLogger("dimsum")


@dataclasses.dataclass
class EditingEntity(StandardEvent):
    entity: Entity
    interactive: bool = True


class EditEntity(PersonAction):
    def __init__(self, item: ItemFinder = None, **kwargs):
        super().__init__(**kwargs)
        assert item
        self.item = item

    async def perform(
        self, world: World, area: Entity, person: Entity, ctx: Ctx, **kwargs
    ):
        item = await world.apply_item_finder(person, self.item)
        if item:
            return EditingEntity(entity=item, living=person, area=area, heard=[])
        return Failure("where's that?")


@dataclasses.dataclass
class ScreenCleared(Reply):
    pass


class ClearScreen(PersonAction):
    async def perform(
        self, world: World, area: Entity, person: Entity, ctx: Ctx, **kwargs
    ):
        return ScreenCleared()


@grammars.grammar()
class Grammar(grammars.Grammar):
    @property
    def evaluator(self):
        return Evaluator

    @property
    def lark(self) -> str:
        return """
        start:             edit_entity | clear_screen

        edit_entity:       ("edit" | "ed") noun
        clear_screen:      "cls"
"""


class Evaluator(BaseEvaluator):
    def edit_entity(self, args):
        return EditEntity(args[0])

    def clear_screen(self, args):
        return ClearScreen()
