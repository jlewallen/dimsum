import logging
from typing import Type, Optional

from context import Ctx
from model.game import *
from model.reply import *
from model.world import *
from model.things import *
import model.scopes.users as users
from plugins.actions import *
import grammars
import transformers

log = logging.getLogger("dimsum")


class LookInside(PersonAction):
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
            return Failure("inside what?")

        with item.make(carryable.Containing) as contain:
            if not contain.is_open():
                return Failure("you can't do that")

            return EntitiesObservation(contain.holding)


class LookFor(PersonAction):
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
            return Failure("i can't seem to find that")

        with person.make(mechanics.Visibility) as vis:
            vis.add_observation(item.identity)

        with person.make(carryable.Containing) as contain:
            return EntitiesObservation([item])


class LookMyself(PersonAction):
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
        return PersonalObservation(person)


class LookDown(PersonAction):
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
        with person.make(carryable.Containing) as contain:
            return EntitiesObservation(contain.holding)


class Look(PersonAction):
    def __init__(self, item=None, **kwargs):
        super().__init__(**kwargs)
        self.item = item

    async def perform(
        self,
        world: World,
        area: entity.Entity,
        person: entity.Entity,
        ctx: Ctx,
        **kwargs
    ):
        if self.item:
            return DetailedObservation(ObservedItem(self.item))

        assert area
        return AreaObservation(area, person)


class Transformer(transformers.Base):
    def look(self, args):
        return Look()

    def look_down(self, args):
        return LookDown()

    def look_myself(self, args):
        return LookMyself()

    def look_item(self, args):
        return Look(item=args[0])

    def look_for(self, args):
        return LookFor(item=args[0])

    def look_inside(self, args):
        return LookInside(item=args[0])


@grammars.grammar()
class LookingGrammar(grammars.Grammar):
    @property
    def transformer_factory(self) -> Type[transformers.Base]:
        return Transformer

    @property
    def lark(self) -> str:
        return """
        start:             look

        look:              "look"
                         | "look" ("down")                         -> look_down
                         | "look" ("at" "myself")                  -> look_myself
                         | "look" ("at" noun)                      -> look_item
                         | "look" ("for" noun)                     -> look_for
                         | "look" ("in" held)                      -> look_inside
"""
