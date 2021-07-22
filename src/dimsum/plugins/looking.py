import dataclasses
from typing import Type, Optional, List, Sequence, Dict, Any, Callable

import grammars
import transformers
import tools
from loggers import get_logger
from model import *
from finders import *
from plugins.actions import PersonAction
import scopes.users as users
import scopes.movement as movement
import scopes.ownership as owning

log = get_logger("dimsum")


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

    def render_tree(self) -> Dict[str, Any]:
        owner = owning.get_owner(self.item.entity)
        return {
            "title": self.item.entity.props.described,
            "description": [
                self.item.entity.props.desc,
                "\n",
                f"Owner: {owner.props.described}",
            ],
        }


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
        def filter_items(predicate: Callable) -> List[ObservedEntity]:
            return list(filter(lambda oe: predicate(oe.entity), self.items))

        distinct_items = filter_items(tools.is_presence_distinct)
        inline_shorts = filter_items(tools.is_presence_inline_short)
        inline_longs = filter_items(tools.is_presence_inline_long)

        emd = [self.area.props.desc]

        if len(inline_shorts) > 0:
            emd[0] += "  You can see " + infl.join(
                [x.entity.describe() for x in inline_shorts]
            )

        emd += [e.entity.props.desc for e in inline_longs]

        if len(self.living) > 0:
            emd += [
                "Also here is " + infl.join([x.entity.describe() for x in self.living])
            ]

        if len(distinct_items) > 0:
            emd += [
                "You can see "
                + infl.join([x.entity.describe() for x in distinct_items])
            ]

        holding = tools.get_holding(self.person)
        if len(holding) > 0:
            emd += ["You're holding " + infl.join([x.describe() for x in holding])]

        return {"title": self.area.props.name, "description": emd}


@dataclasses.dataclass
class EntitiesObservation(Observation):
    entities: Sequence[Entity]

    def render_tree(self) -> Dict[str, Any]:
        if len(self.entities) == 0:
            return {"lines": ["You see nothing."]}
        return {
            "lines": ["You see " + infl.join([x.describe() for x in self.entities])]
        }


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
            return Failure("Inside what?")

        with item.make(carryable.Containing) as contain:
            if not contain.is_open():
                return Failure("You can't do that.")

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
            return Failure("I can't seem to find that.")

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
    def __init__(self, item: Optional[ItemFinder] = None, **kwargs):
        super().__init__(**kwargs)
        self.item = item

    async def perform(
        self, world: World, area: Entity, person: Entity, ctx: Ctx, **kwargs
    ):
        if self.item:
            item = await ctx.apply_item_finder(person, self.item)
            if not item:
                return Failure("Look at what?")
            return DetailedObservation(ObservedEntity(item))

        assert area
        return AreaObservation(area, person)


class Examine(PersonAction):
    def __init__(self, item: ItemFinder, **kwargs):
        super().__init__(**kwargs)
        self.item = item

    async def perform(
        self, world: World, area: Entity, person: Entity, ctx: Ctx, **kwargs
    ):
        item = await ctx.apply_item_finder(person, self.item)
        if not item:
            return Failure("Examine what?")
        return DetailedObservation(ObservedEntity(item))


class ModifyPresence(PersonAction):
    def __init__(self, item: ItemFinder, presence: mechanics.Presence, **kwargs):
        super().__init__(**kwargs)
        self.item = item
        self.presence = presence

    async def perform(
        self, world: World, area: Entity, person: Entity, ctx: Ctx, **kwargs
    ):
        item = await ctx.apply_item_finder(person, self.item)
        if not item:
            return Failure("Modify what?")

        tools.set_presence(item, self.presence)

        return DetailedObservation(ObservedEntity(item))


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

    def examine(self, args):
        return Examine(item=args[0])

    def presence_distinct(self, args):
        return ModifyPresence(args[0], mechanics.Presence.DISTINCT)

    def presence_inline_short(self, args):
        return ModifyPresence(args[0], mechanics.Presence.INLINE_SHORT)

    def presence_inline_long(self, args):
        return ModifyPresence(args[0], mechanics.Presence.INLINE_LONG)


@grammars.grammar()
class LookingGrammar(grammars.Grammar):
    @property
    def transformer_factory(self) -> Type[transformers.Base]:
        return Transformer

    @property
    def lark(self) -> str:
        return """
        start:             look | examine | modify

        look:              "look"
                         | "look" ("down")                           -> look_down
                         | "look" ("at" "myself")                    -> look_myself
                         | "look" ("at" noun)                        -> look_item
                         | "look" ("for" noun)                       -> look_for
                         | "look" ("in" held)                        -> look_inside

                         // Order of here and noun is important.
        examine:           "examine" (here | noun)                   -> examine

        modify:            "modify" "presence" noun "distinct"       -> presence_distinct
                         | "modify" "presence" noun "inline" "short" -> presence_inline_short
                         | "modify" "presence" noun "inline" "long"  -> presence_inline_long
"""


def flatten(l):
    return [item for sl in l for item in sl]
