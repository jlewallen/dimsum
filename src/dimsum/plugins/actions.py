import dataclasses
from typing import List, Dict, Optional, Any

import tools
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


class AddItemArea(PersonAction):
    def __init__(self, item=None, area=None, **kwargs):
        super().__init__(**kwargs)
        self.item = item
        self.area = area

    async def perform(
        self, world: World, area: Entity, person: Entity, ctx: Ctx, **kwargs
    ):
        with self.area.make(carryable.Containing) as ground:
            after_add = ground.add_item(self.item)
            ctx.register(after_add)

            # We do this after because we may consolidate this Item and
            # this keeps us from having to unregister the item.
            ctx.register(after_add)

        await ctx.publish(
            ItemsAppeared(
                source=person,
                area=self.area,
                heard=tools.default_heard_for(area=area, excepted=[person]),
                items=[self.item],
            )
        )
        return Success("%s appeared" % (infl.join([self.item]),))


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
