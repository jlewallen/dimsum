import dataclasses
import logging
from typing import Any, List, Optional

from context import Ctx
import model.entity as entity
from model.events import *
import model.finders as finders
from model.game import *
import model.properties as properties
from model.reply import *
import model.scopes.apparel as apparel
import model.scopes.carryable as carryable
import model.scopes.health as health
import model.scopes.mechanics as mechanics
import model.scopes.movement as movement
from model.things import *
from model.tools import *
from model.world import *
from plugins.actions import *

MemoryAreaKey = "m:area"
log = logging.getLogger("dimsum")


@event
@dataclasses.dataclass(frozen=True)
class ItemsAppeared(StandardEvent):
    items: List[entity.Entity]


@event
@dataclasses.dataclass(frozen=True)
class PlayerJoined(StandardEvent):
    pass


class AddItemArea(PersonAction):
    def __init__(self, item=None, area=None, **kwargs):
        super().__init__(**kwargs)
        self.item = item
        self.area = area

    async def perform(
        self,
        world: World,
        area: entity.Entity,
        person: entity.Entity,
        ctx: Ctx,
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
                heard=default_heard_for(area=area),
                items=[self.item],
            )
        )
        return Success("%s appeared" % (p.join([self.item]),))


class Join(PersonAction):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def perform(
        self,
        world: World,
        area: entity.Entity,
        person: entity.Entity,
        ctx: Ctx,
        **kwargs
    ):
        ctx.register(person)
        with world.welcome_area().make(occupyable.Occupyable) as entering:
            await ctx.publish(
                PlayerJoined(
                    living=person,
                    area=entering.ourselves,
                    heard=default_heard_for(area=area),
                )
            )
            await entering.entered(person)
        return Success("welcome!")


class ModifyHardToSee(PersonAction):
    def __init__(self, item: Optional[ItemFinder] = None, hard_to_see=False, **kwargs):
        super().__init__(**kwargs)
        assert item
        self.item = item
        self.hard_to_see = hard_to_see

    async def perform(
        self,
        world: World,
        area: entity.Entity,
        person: entity.Entity,
        ctx: Ctx,
        **kwargs
    ):
        item = await world.apply_item_finder(person, self.item)
        if not item:
            return Failure("of what?")

        item.try_modify()

        with item.make(mechanics.Visibility) as vis:
            if self.hard_to_see:
                vis.make_hard_to_see()
            else:
                vis.make_easy_to_see()

        return Success("done")


class ModifyField(PersonAction):
    def __init__(self, item=None, field=None, value=None, **kwargs):
        super().__init__(**kwargs)
        self.item = item
        self.field = field
        self.value = value

    async def perform(
        self,
        world: World,
        area: entity.Entity,
        person: entity.Entity,
        ctx: Ctx,
        **kwargs
    ):
        item = await world.apply_item_finder(person, self.item)
        if not item:
            return Failure("of what?")

        item.try_modify()

        if self.field in health.NutritionFields:
            with item.make(health.Edible) as i:
                i.nutrition.properties[self.field] = self.value
        else:
            item.props.set(self.field, self.value)

        item.touch()

        return Success("done")


class ModifyActivity(PersonAction):
    def __init__(
        self, item: Optional[ItemFinder] = None, activity=None, value=None, **kwargs
    ):
        super().__init__(**kwargs)
        assert item
        self.item = item
        assert activity
        self.activity = activity
        assert value
        self.value = value

    async def perform(
        self,
        world: World,
        area: entity.Entity,
        person: entity.Entity,
        ctx: Ctx,
        **kwargs
    ):
        item = await world.apply_item_finder(person, self.item)
        if not item:
            return Failure("of what?")

        item.try_modify()
        with item.make(mechanics.Interactable) as inaction:
            inaction.link_activity(self.activity, self.value)
        item.props.set(self.activity, self.value)
        item.touch()
        return Success("done")
