import dataclasses
from typing import Optional, Type

import grammars
import transformers
from loggers import get_logger
from model import *
from finders import *
from plugins.actions import PersonAction
import scopes.mechanics as mechanics
import scopes.health as health
import tools

log = get_logger("dimsum")


@event
@dataclasses.dataclass(frozen=True)
class EditingEntityBehavior(StandardEvent):
    entity: Entity
    interactive: bool = True


class EditEntity(PersonAction):
    def __init__(self, item: Optional[ItemFinder] = None, **kwargs):
        super().__init__(**kwargs)
        assert item
        self.item = item

    async def perform(
        self, world: World, area: Entity, person: Entity, ctx: Ctx, **kwargs
    ):
        item = await ctx.apply_item_finder(person, self.item)
        if item:
            return EditingEntityBehavior(
                source=person, area=area, heard=[], entity=item
            )
        return Failure("Where's that?")


@dataclasses.dataclass(frozen=True)
class ScreenCleared(Reply):
    pass


class ClearScreen(PersonAction):
    async def perform(
        self, world: World, area: Entity, person: Entity, ctx: Ctx, **kwargs
    ):
        return ScreenCleared()


class ModifyHardToSee(PersonAction):
    def __init__(self, item: Optional[ItemFinder] = None, hard_to_see=False, **kwargs):
        super().__init__(**kwargs)
        assert item
        self.item = item
        self.hard_to_see = hard_to_see

    async def perform(
        self, world: World, area: Entity, person: Entity, ctx: Ctx, **kwargs
    ):
        item = await ctx.apply_item_finder(person, self.item)
        if not item:
            return Failure("Modify what?")

        item.try_modify()

        with item.make(mechanics.Visibility) as vis:
            if self.hard_to_see:
                vis.make_hard_to_see()
            else:
                vis.make_easy_to_see()

        return Success("Done!")


class ModifyField(PersonAction):
    def __init__(self, item=None, field=None, value=None, **kwargs):
        super().__init__(**kwargs)
        self.item = item
        self.field = field
        self.value = value

    async def perform(
        self, world: World, area: Entity, person: Entity, ctx: Ctx, **kwargs
    ):
        item = await ctx.apply_item_finder(person, self.item)
        if not item:
            return Failure("Modify what?")

        item.try_modify()

        if self.field in health.NutritionFields:
            with item.make(health.Edible) as i:
                i.nutrition.properties[self.field] = self.value
        else:
            item.props.set(self.field, self.value)
            # Fix untouched save of container, as references contain
            # names and this will trigger the untouched save detector.
            if self.field == "name":  # HACK
                tools.container(item).touch()

        item.touch()

        return Success("Done!")


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
        self, world: World, area: Entity, person: Entity, ctx: Ctx, **kwargs
    ):
        item = await ctx.apply_item_finder(person, self.item)
        if not item:
            return Failure("Modify what?")

        item.try_modify()
        with item.make(mechanics.Interactable) as inaction:
            inaction.link_activity(self.activity, self.value)
        item.props.set(self.activity, self.value)
        item.touch()
        return Success("Done!")


@grammars.grammar()
class Grammar(grammars.Grammar):
    @property
    def order(self) -> int:
        return grammars.LOWEST

    @property
    def transformer_factory(self) -> Type[transformers.Base]:
        return Transformer

    @property
    def lark(self) -> str:
        return """
        start:             edit_entity | clear_screen | modify

        edit_entity:       ("edit" | "ed") (here | this | noun)
        clear_screen:      "cls"

        modify:            "modify" TEXT_FIELD text                -> modify_field
                         | "modify" NUMERIC_FIELD number           -> modify_field
                         | "modify" "hard" "to" "see"              -> modify_hard_to_see
                         | "modify" "easy" "to" "see"              -> modify_easy_to_see
"""


class Transformer(transformers.Base):
    def edit_entity(self, args):
        return EditEntity(args[0])

    def clear_screen(self, args):
        return ClearScreen()

    def modify_hard_to_see(self, args):
        return ModifyHardToSee(item=AnyHeldItem(), hard_to_see=True)

    def modify_easy_to_see(self, args):
        return ModifyHardToSee(item=AnyHeldItem(), hard_to_see=False)

    def modify_field(self, args):
        field = str(args[0])
        value = args[1]
        return ModifyField(item=AnyHeldItem(), field=field, value=value)
