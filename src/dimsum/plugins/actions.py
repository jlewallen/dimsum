import dataclasses
from typing import List, Dict, Optional

import inflect

import context

import model.entity as entity
import model.game as game
import model.world as world
import model.events as events
import model.reply as reply
import tools

import scopes.carryable as carryable
import scopes.occupyable as occupyable

p = inflect.engine()


class PersonAction(game.Action):
    async def perform(
        self,
        world: world.World,
        area: entity.Entity,
        person: entity.Entity,
        ctx: context.Ctx,
        **kwargs
    ) -> game.Reply:
        raise NotImplementedError


@events.event
@dataclasses.dataclass(frozen=True)
class ItemsAppeared(events.StandardEvent):
    items: List[entity.Entity]


@events.event
@dataclasses.dataclass(frozen=True)
class PlayerJoined(events.StandardEvent):
    pass


class AddItemArea(PersonAction):
    def __init__(self, item=None, area=None, **kwargs):
        super().__init__(**kwargs)
        self.item = item
        self.area = area

    async def perform(
        self,
        world: world.World,
        area: entity.Entity,
        person: entity.Entity,
        ctx: context.Ctx,
        **kwargs
    ):
        with self.area.make(carryable.Containing) as ground:
            after_add = ground.add_item(self.item)
            ctx.register(after_add)

            # We do this after because we may consolidate this Item and
            # this keeps us from having to unregister the item.
            ctx.register(after_add)

        await ctx.publish(
            ItemsAppeared(
                living=person,
                area=self.area,
                heard=tools.default_heard_for(area=area),
                items=[self.item],
            )
        )
        return game.Success("%s appeared" % (p.join([self.item]),))


class Join(PersonAction):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def perform(
        self,
        world: world.World,
        area: entity.Entity,
        person: entity.Entity,
        ctx: context.Ctx,
        **kwargs
    ):
        ctx.register(person)
        with world.welcome_area().make(occupyable.Occupyable) as entering:
            await ctx.publish(
                PlayerJoined(
                    living=person,
                    area=entering.ourselves,
                    heard=tools.default_heard_for(area=area),
                )
            )
            await entering.entered(person)
        return game.Success("welcome!")
