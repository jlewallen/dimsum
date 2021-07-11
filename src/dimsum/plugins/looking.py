import logging
import dataclasses
from typing import Type, Optional, List, Sequence, Dict, Any

import grammars
import transformers
import tools
from model import *
from finders import *
from plugins.actions import PersonAction
import scopes.users as users
import scopes.movement as movement

log = logging.getLogger("dimsum")


class ObservedLiving(ObservedEntity):
    @property
    def activities(self) -> Sequence[Activity]:
        return [
            HoldingActivity(e) for e in self.entity.make(carryable.Containing).holding
        ]

    @property
    def holding(self):
        return self.entity.make(carryable.Containing).holding


@dataclasses.dataclass
class DetailedObservation(Observation):
    item: ObservedEntity


@dataclasses.dataclass
class AreaObservation(Observation):
    area: Entity
    person: Entity

    def __post_init__(self):
        occupied = self.area.make(occupyable.Occupyable).occupied
        self.living: List[ObservedLiving] = flatten(
            [observe_entity(e) for e in occupied if e != self.person]
        )

        self.items: List[ObservedEntity] = flatten(
            [
                observe_entity(e)
                for e in self.area.make(carryable.Containing).holding
                if not e.make(mechanics.Visibility).visible.hard_to_see
                or self.person.make(mechanics.Visibility).can_see(e.identity)
            ]
        )
        self.routes: List[movement.AreaRoute] = self.area.make(
            movement.Movement
        ).available_routes

    def render_tree(self) -> Dict[str, Any]:
        emd = [self.area.props.desc]
        if len(self.living) > 0:
            emd += [
                "Also here is " + infl.join([x.entity.describe() for x in self.living])
            ]
        if len(self.items) > 0:
            emd += [
                "You can see " + infl.join([x.entity.describe() for x in self.items])
            ]
        holding = tools.get_holding(self.person)
        if len(holding) > 0:
            emd += ["You're holding " + infl.join([x.describe() for x in holding])]
        return {"title": self.area.props.name, "description": emd}


@dataclasses.dataclass
class EntitiesObservation(Observation):
    entities: Sequence[Entity]


@dataclasses.dataclass
class PersonalObservation(Observation):
    who: Entity


class LookInside(PersonAction):
    def __init__(self, item: Optional[ItemFinder] = None, **kwargs):
        super().__init__(**kwargs)
        assert item
        self.item = item

    async def perform(
        self, world: World, area: Entity, person: Entity, ctx: Ctx, **kwargs
    ):
        item = await ctx.apply_item_finder(person, self.item)
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
        self, world: World, area: Entity, person: Entity, ctx: Ctx, **kwargs
    ):
        item = await ctx.apply_item_finder(person, self.item)
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
        self, world: World, area: Entity, person: Entity, ctx: Ctx, **kwargs
    ):
        return PersonalObservation(person)


class LookDown(PersonAction):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def perform(
        self, world: World, area: Entity, person: Entity, ctx: Ctx, **kwargs
    ):
        with person.make(carryable.Containing) as contain:
            return EntitiesObservation(contain.holding)


class Look(PersonAction):
    def __init__(self, item=None, **kwargs):
        super().__init__(**kwargs)
        self.item = item

    async def perform(
        self, world: World, area: Entity, person: Entity, ctx: Ctx, **kwargs
    ):
        if self.item:
            return DetailedObservation(ObservedEntity(self.item))

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


def flatten(l):
    return [item for sl in l for item in sl]
