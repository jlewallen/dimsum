import logging
import dataclasses
from typing import Type, Optional, List

from context import Ctx
from model.game import *
from model.reply import *
from model.world import *
from model.things import *
from model.finders import *
from model.events import *
from model.tools import *
import model.properties
import model.scopes.health as health
from plugins.actions import *
import grammars
import transformers

import plugins.default.actions as actions

log = logging.getLogger("dimsum")


class ModifyServings(PersonAction):
    def __init__(self, item: Optional[ItemFinder] = None, number=None, **kwargs):
        super().__init__(**kwargs)
        assert item
        self.item = item
        assert number
        self.number = number

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
            return Failure("nothing to modify")

        item.try_modify()

        with item.make(health.Edible) as edible:
            edible.modify_servings(self.number)

        item.touch()

        return Success("done")


class Eat(PersonAction):
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
            return Failure("dunno where that is")

        with item.make(mechanics.Interactable) as inaction:
            if not inaction.when_eaten():
                return Failure("you can't eat that")

        area = world.find_person_area(person)
        with person.make(health.Health) as p:
            await p.consume(item, area=area, ctx=ctx)

        return Success("you ate %s" % (item))


class Drink(PersonAction):
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
            return Failure("dunno where that is")

        with item.make(mechanics.Interactable) as inaction:
            if not inaction.when_drank():
                return Failure("you can't drink that")

        area = world.find_person_area(person)
        with person.make(health.Health) as p:
            await p.consume(item, area=area, ctx=ctx)

        return Success("you drank %s" % (item))


class Transformer(transformers.Base):
    def eat(self, args):
        return Eat(item=args[0])

    def drink(self, args):
        return Drink(item=args[0])

    def modify_servings(self, args):
        return ModifyServings(item=AnyHeldItem(), number=args[0])

    def when_eaten(self, args):
        return actions.ModifyActivity(
            item=AnyHeldItem(), activity=properties.Eaten, value=True
        )

    def when_drank(self, args):
        return actions.ModifyActivity(
            item=AnyHeldItem(), activity=properties.Drank, value=True
        )


@grammars.grammar()
class ClothingGrammar(grammars.Grammar):
    @property
    def transformer_factory(self) -> Type[transformers.Base]:
        return Transformer

    @property
    def lark(self) -> str:
        return """
        start:             eat | drink | modify

        eat:               "eat" consumable
        drink:             "drink" consumable

        modify:            "modify" "when" "eaten"                 -> when_eaten
                         | "modify" "when" "drank"                 -> when_drank
                         | "modify" "servings" number              -> modify_servings
"""
