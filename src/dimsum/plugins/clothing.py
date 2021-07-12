import logging
import dataclasses
from typing import Type, Optional, List, Dict, Any

import grammars
import transformers
from model import *
from tools import *
from finders import *
from plugins.actions import PersonAction
from plugins.editing import ModifyActivity
import scopes.apparel as apparel

log = logging.getLogger("dimsum")


@event
@dataclasses.dataclass(frozen=True)
class ItemsWorn(StandardEvent):
    items: List[Entity]

    def render_tree(self) -> Dict[str, Any]:
        return {
            "lines": [
                f"{self.source.props.described} wore {self.render_entities(self.items)}"
            ]
        }


@event
@dataclasses.dataclass(frozen=True)
class ItemsUnworn(StandardEvent):
    items: List[Entity]

    def render_tree(self) -> Dict[str, Any]:
        return {
            "lines": [
                f"{self.source.props.described} took off {self.render_entities(self.items)}"
            ]
        }


class Wear(PersonAction):
    def __init__(self, item: Optional[ItemFinder] = None, **kwargs):
        super().__init__(**kwargs)
        assert item
        self.item = item

    async def perform(
        self, world: World, area: Entity, person: Entity, ctx: Ctx, **kwargs
    ):
        item = await ctx.apply_item_finder(person, self.item)
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
                source=person,
                area=area,
                heard=default_heard_for(area=area, excepted=[person]),
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
        self, world: World, area: Entity, person: Entity, ctx: Ctx, **kwargs
    ):
        item = await ctx.apply_item_finder(person, self.item)
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
                source=person,
                area=area,
                heard=default_heard_for(area=area, excepted=[person]),
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
        return ModifyActivity(item=AnyHeldItem(), activity=Worn, value=True)


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
