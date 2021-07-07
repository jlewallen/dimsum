import dataclasses
import logging
from typing import Any, Dict, List, Sequence

import inflect
import model.entity as entity
import model.game as game
import model.scopes.carryable as carryable
import model.scopes.mechanics as mechanics
import model.scopes.movement as movement
import model.scopes.occupyable as occupyable
import model.visual as visual

p = inflect.engine()
log = logging.getLogger("dimsum.model")


class Observation(game.Reply, visual.Renderable):
    def render_string(self) -> Dict[str, str]:
        return {"message": "some kind of observation"}


@dataclasses.dataclass
class ObservedEntity:
    entity: entity.Entity


class ObservedItem(ObservedEntity):
    def accept(self, visitor):
        return visitor.observed_entity(self)

    def __str__(self):
        return str(self.entity)

    def __repr__(self):
        return str(self)


class Activity:
    pass


class HoldingActivity(Activity):
    def __init__(self, item: entity.Entity):
        super().__init__()
        self.item = item

    def __str__(self):
        return "holding %s" % (self.item,)


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


class ObservedEntities:
    def __init__(self, entities: List[entity.Entity]):
        super().__init__()
        self.entities = entities

    def __str__(self):
        return str(p.join(self.entities))

    def __repr__(self):
        return str(self)


class PersonalObservation(Observation):
    def __init__(self, who: entity.Entity):
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


class EntitiesObservation(Observation):
    def __init__(self, entities: Sequence[entity.Entity]):
        super().__init__()
        self.entities = entities

    @property
    def items(self):
        return self.entities

    def accept(self, visitor):
        return visitor.entities_observation(self)

    def __str__(self):
        return "observed %s" % (p.join(self.entities),)


class AreaObservation(Observation):
    def __init__(self, area: entity.Entity, person: entity.Entity):
        super().__init__()
        assert area
        assert person
        self.who: ObservedPerson = ObservedPerson(person)
        self.where: entity.Entity = area

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


def observe(entity: Any) -> Sequence[ObservedEntity]:
    if entity.make(mechanics.Visibility).is_invisible:
        return []
    return [ObservedItem(entity)]


def flatten(l):
    return [item for sl in l for item in sl]
