import dataclasses
from typing import List, Dict, Optional, Any

import tools
from loggers import get_logger
from model import (
    Entity,
    World,
    Action,
    Ctx,
    Reply,
    event,
    StandardEvent,
    Success,
    infl,
    materialize_well_known_entity,
    WelcomeAreaKey,
)
import scopes.carryable as carryable
import scopes.occupyable as occupyable


class PersonAction(Action):
    async def perform(
        self, world: World, area: Entity, person: Entity, ctx: Ctx, **kwargs
    ) -> Reply:
        raise NotImplementedError


@event
@dataclasses.dataclass(frozen=True)
class ItemsAppeared(StandardEvent):
    items: List[Entity]

    def render_tree(self) -> Dict[str, Any]:
        return {
            "text": f"{self.source.props.name} appeared {self.render_entities(self.items)}"
        }


@event
@dataclasses.dataclass(frozen=True)
class PlayerJoined(StandardEvent):
    def render_tree(self) -> Dict[str, Any]:
        return {"text": f"{self.source.props.name} joined"}


class Join(PersonAction):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def perform(
        self, world: World, area: Entity, person: Entity, ctx: Ctx, **kwargs
    ):
        ctx.register(person)

        welcome_area = await materialize_well_known_entity(world, ctx, WelcomeAreaKey)
        with welcome_area.make(occupyable.Occupyable) as entering:
            await ctx.publish(
                PlayerJoined(
                    source=person,
                    area=entering.ourselves,
                    heard=tools.default_heard_for(area=area, excepted=[person]),
                )
            )
            await entering.entered(person)
        return Success("welcome!")
