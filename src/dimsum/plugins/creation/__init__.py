from typing import Any, List, Type

import logging

import model.properties as properties
import model.scopes as scopes

import grammars

from model.entity import *
from model.world import *
from model.events import *
from model.things import *
from model.reply import *
from model.finders import *

from plugins.actions import *
from context import *

log = logging.getLogger("dimsum")


@dataclasses.dataclass
class EntityCreated(StandardEvent):
    entity: Entity

    def render_string(self) -> Dict[str, str]:
        return {"text": f"{self.living.props.name} created '{self.entity.props.name}'"}


class Create(PersonAction):
    def __init__(self, scopes: List[Type] = None, **kwargs):
        super().__init__(**kwargs)
        assert scopes
        self.scopes = scopes

    async def perform(
        self, world: World, area: Entity, person: Entity, ctx: Ctx, **kwargs
    ):
        log.info("creating %s", self.scopes)
        return Success()


@grammars.grammar()
class Grammar(grammars.Grammar):
    @property
    def evaluator(self):
        return Evaluator

    @property
    def lark(self) -> str:
        return """
        start:                  create

        create:                 "create" create_entity_kind TEXT
        create_entity_kind:     "thing" -> create_entity_kind_thing
                              | "area" -> create_entity_kind_area
                              | "exit" -> create_entity_kind_exit
                              | "living" -> create_entity_kind_living

"""


class Evaluator(BaseEvaluator):
    def create(self, args):
        log.info("create: %s", args[0])
        return Create(args[0])

    def create_entity_kind_thing(self, args):
        return scopes.Item

    def create_entity_kind_area(self, args):
        return scopes.Area

    def create_entity_kind_exit(self, args):
        return scopes.Exit

    def create_entity_kind_living(self, args):
        return scopes.Alive
