import logging
import dataclasses
from typing import Type, Optional, List

from context import Ctx
from model.game import *
from model.reply import *
from model.world import *
from model.events import *
import scopes.apparel as apparel
from plugins.actions import *
from tools import *
from finders import *
import grammars
import transformers

import plugins.default as actions

log = logging.getLogger("dimsum")


@event
@dataclasses.dataclass(frozen=True)
class ItemsWorn(StandardEvent):
    items: List[entity.Entity]


@event
@dataclasses.dataclass(frozen=True)
class ItemsUnworn(StandardEvent):
    items: List[entity.Entity]


class Wear(PersonAction):
    def __init__(self, item: Optional[ItemFinder] = None, **kwargs):
        super().__init__(**kwargs)
        assert item
        self.item = item

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
            return Failure("wear what?")

        with item.make(mechanics.Interactable) as inaction:
            if not inaction.when_worn():
                return Failure("you can't wear that")

        with person.make(carryable.Containing) as contain:
            assert contain.is_holding(item)

            with person.make(apparel.Apparel) as wearing:
                if wearing.wear(item):
                    contain.drop(item)

        await ctx.publish(
            ItemsWorn(
                living=person,
                area=area,
                heard=default_heard_for(area=area),
                items=[item],
            )
        )
        return Success("you wore %s" % (item))


class Remove(PersonAction):
    def __init__(self, item: Optional[ItemFinder] = None, **kwargs):
        super().__init__(**kwargs)
        assert item
        self.item = item

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
            return Failure("remove what?")

        with person.make(apparel.Apparel) as wearing:
            if not wearing.is_wearing(item):
                return Failure("you aren't wearing that")

            assert wearing.is_wearing(item)

            if wearing.unwear(item):
                with person.make(carryable.Containing) as contain:
                    contain.hold(item)

        await ctx.publish(
            ItemsUnworn(
                living=person,
                area=area,
                heard=default_heard_for(area=area),
                items=[item],
            )
        )
        return Success("you removed %s" % (item))


class Transformer(transformers.Base):
    def wear(self, args):
        return Wear(item=args[0])

    def remove(self, args):
        return Remove(item=args[0])

    def when_worn(self, args):
        return actions.ModifyActivity(
            item=AnyHeldItem(), activity=properties.Worn, value=True
        )


@grammars.grammar()
class ClothingGrammar(grammars.Grammar):
    @property
    def transformer_factory(self) -> Type[transformers.Base]:
        return Transformer

    @property
    def lark(self) -> str:
        return """
        start:             wear | remove | modify

        wear:              "wear" noun
        remove:            "remove" noun

        modify:            "modify" "when" "worn"                  -> when_worn

"""
