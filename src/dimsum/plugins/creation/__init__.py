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


def default_heard_for(area: entity.Entity = None) -> List[entity.Entity]:
    if area:
        with area.make_and_discard(occupyable.Occupyable) as here:
            return here.occupied
    return []


class Create(PersonAction):
    def __init__(
        self,
        klass: Type[EntityClass],
        name: str = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        assert klass
        assert name
        self.klass = klass
        self.name = name

    async def perform(
        self, world: World, area: Entity, person: Entity, ctx: Ctx, **kwargs
    ):
        log.info("creating '%s' klass=%s", self.name, self.klass)
        created = scopes.create_klass(
            self.klass,
            creator=person,
            props=properties.Common(name=self.name, desc=self.name),
        )  # TODO create
        with person.make(carryable.Containing) as contain:
            after_hold = contain.hold(created)
            # We do this after because we may consolidate this Item and
            # this keeps us from having to unregister the item.
            ctx.register(after_hold)
            return EntityCreated(
                area=area,
                living=person,
                entity=after_hold,
                heard=default_heard_for(area),
            )


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
        return Create(args[0], str(args[1]))

    def create_entity_kind_thing(self, args):
        return scopes.ItemClass

    def create_entity_kind_area(self, args):
        return scopes.AreaClass

    def create_entity_kind_exit(self, args):
        return scopes.ExitClass

    def create_entity_kind_living(self, args):
        return scopes.AliveClass
