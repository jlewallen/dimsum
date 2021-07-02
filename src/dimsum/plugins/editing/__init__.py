from typing import Any, List, Type

import logging

import grammars

from model.entity import *
from model.world import *
from model.events import *
from model.things import *
from model.reply import *

from plugins.actions import *
from context import *

log = logging.getLogger("dimsum")


@dataclasses.dataclass
class EditableEntity(StandardEvent):
    entity: Entity


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
            return EditableEntity(entity=item, living=person, area=area, heard=[])
        return Failure("where's that?")


@grammars.grammar()
class Grammar(grammars.Grammar):
    @property
    def evaluator(self):
        return Evaluator

    @property
    def lark(self) -> str:
        return """
        start:             edit_entity

        edit_entity:       ("edit" | "ed") noun
"""


class Evaluator(BaseEvaluator):
    def edit_entity(self, args):
        return EditEntity(args[0])
