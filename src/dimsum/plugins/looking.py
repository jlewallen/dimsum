import logging
import dataclasses
import inflect
from typing import Type, Optional, List, Sequence, Dict

import grammars
import transformers
from model import *
from finders import *
from plugins.actions import PersonAction
import scopes.users as users
import scopes.movement as movement

log = logging.getLogger("dimsum")
p = inflect.engine()


class ObservedLiving(ObservedEntity):
    @property
    def activities(self) -> Sequence[Activity]:
        return [
            HoldingActivity(e) for e in self.entity.make(carryable.Containing).holding
        ]

    @property
    def holding(self):
        return self.entity.make(carryable.Containing).holding

    @property
    def memory(self):
        return self.entity.make(mechanics.Memory).memory

    def __str__(self):
        if len(self.activities) == 0:
            return "%s" % (self.entity,)
        return "%s who is %s" % (self.entity, p.join(list(map(str, self.activities))))

    def __repr__(self):
        return str(self)


class ObservedAnimal(ObservedLiving):
    @property
    def animal(self):
        return self.entity


class ObservedPerson(ObservedLiving):
    @property
    def person(self):
        return self.entity


@dataclasses.dataclass
class DetailedObservation(Observation):
    item: ObservedEntity

    @property
    def props(self):
        return self.item.entity.props

    @property
    def properties(self):
        return self.props.map

    def accept(self, visitor):
        return visitor.detailed_observation(self)

    def __str__(self):
        return "observed %s %s" % (
            self.item,
            self.properties,
        )


class AreaObservation(Observation):
    def __init__(self, area: Entity, person: Entity):
        super().__init__()
        assert area
        assert person
        self.who: ObservedPerson = ObservedPerson(person)
        self.where: Entity = area

        occupied = area.make(occupyable.Occupyable).occupied
        self.living: List[ObservedLiving] = flatten(
            [observe(e) for e in occupied if e != person]
        )

        self.items: List[ObservedEntity] = flatten(
            [
                observe(e)
                for e in area.make(carryable.Containing).holding
                if not e.make(mechanics.Visibility).visible.hard_to_see
                or person.make(mechanics.Visibility).can_see(e.identity)
            ]
        )
        self.routes: List[movement.AreaRoute] = area.make(
            movement.Movement
        ).available_routes

    @property
    def props(self):
        return self.where.props

    def accept(self, visitor):
        return visitor.area_observation(self)

    def __str__(self):
        return "%s observes %s, also here %s and visible is %s" % (
            self.who,
            self.props,
            self.living,
            self.items,
        )

    def render_string(self) -> Dict[str, str]:
        emd = self.props.desc
        emd += "\n\n"
        if len(self.living) > 0:
            emd += "Also here: " + p.join([str(x) for x in self.living])
            emd += "\n"
        if len(self.items) > 0:
            emd += "You can see " + p.join([str(x) for x in self.items])
            emd += "\n"
        if len(self.who.holding) > 0:
            emd += "You're holding " + p.join([str(x) for x in self.who.holding])
            emd += "\n"
        directional = [
            e for e in self.routes if isinstance(e, movement.DirectionalRoute)
        ]
        if len(directional) > 0:
            directions = [d.direction for d in directional]
            emd += "You can go " + p.join([str(d) for d in directions])
            emd += "\n"
        return {"title": self.props.name, "description": emd}


class EntitiesObservation(Observation):
    def __init__(self, entities: Sequence[Entity]):
        super().__init__()
        self.entities = entities

    @property
    def items(self):
        return self.entities

    def accept(self, visitor):
        return visitor.entities_observation(self)

    def __str__(self):
        return "observed %s" % (p.join(self.entities),)


class PersonalObservation(Observation):
    def __init__(self, who: Entity):
        super().__init__()
        self.who = ObservedPerson(who)

    @property
    def props(self):
        return self.who.person.props

    @property
    def properties(self):
        return self.props.map

    @property
    def memory(self):
        return self.who.person.make(mechanics.Memory).memory

    def accept(self, visitor):
        return visitor.personal_observation(self)

    def __str__(self):
        return "%s considers themselves %s" % (
            self.who,
            self.properties,
        )


class LookInside(PersonAction):
    def __init__(self, item: Optional[ItemFinder] = None, **kwargs):
        super().__init__(**kwargs)
        assert item
        self.item = item

    async def perform(
        self, world: World, area: Entity, person: Entity, ctx: Ctx, **kwargs
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
        self, world: World, area: Entity, person: Entity, ctx: Ctx, **kwargs
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
