from typing import List, Sequence, Any
import logging
import inflect
import entity
import game
import things
import envo
import movement
import mechanics
import occupyable
import carryable
import living

p = inflect.engine()
log = logging.getLogger("dimsum")


class Observable:
    pass


class Observation(game.Reply, Observable):
    pass


class ObservedEntity(Observable):
    pass


class ObservedItem(ObservedEntity):
    def __init__(self, item: things.Item):
        super().__init__()
        self.item = item

    def accept(self, visitor):
        return visitor.observed_entity(self)

    def __str__(self):
        return str(self.item)

    def __repr__(self):
        return str(self)


class ObservedLiving(ObservedEntity):
    def __init__(self, alive: entity.Entity):
        super().__init__()
        self.alive = alive
        self.activities: Sequence[living.Activity] = [
            living.HoldingActivity(e)
            for e in things.expected(alive.make(carryable.ContainingMixin).holding)
        ]

    @property
    def holding(self):
        return self.alive.make(carryable.ContainingMixin).holding

    @property
    def memory(self):
        return self.alive.make(mechanics.MemoryMixin).memory

    def accept(self, visitor):
        return visitor.observed_living(self)

    def __str__(self):
        if len(self.activities) == 0:
            return "%s" % (self.alive,)
        return "%s who is %s" % (self.alive, p.join(list(map(str, self.activities))))

    def __repr__(self):
        return str(self)


class ObservedAnimal(ObservedLiving):
    def accept(self, visitor):
        return visitor.observed_animal(self)

    @property
    def animal(self):
        return self.living


class ObservedPerson(ObservedLiving):
    def accept(self, visitor):
        return visitor.observed_person(self)

    @property
    def person(self):
        return self.alive


class ObservedEntities(Observable):
    def __init__(self, entities: List[entity.Entity]):
        super().__init__()
        self.entities = entities

    def accept(self, visitor):
        return visitor.observed_entities(self)

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
        return self.who.make(mechanics.MemoryMixin).memory

    def accept(self, visitor):
        return visitor.personal_observation(self)

    def __str__(self):
        return "%s considers themselves %s" % (
            self.who,
            self.properties,
        )


class DetailedObservation(Observation):
    def __init__(self, item: ObservedEntity):
        super().__init__()
        self.item = item

    @property
    def props(self):
        return self.item.props

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
    def __init__(self, area: envo.Area, person: entity.Entity):
        super().__init__()
        assert area
        assert person
        self.who: ObservedPerson = ObservedPerson(person)
        self.where: envo.Area = area
        self.living: List[ObservedLiving] = flatten(
            [
                observe(e)
                for e in area.make(occupyable.OccupyableMixin).occupied
                if e != person
            ]
        )
        self.items: List[ObservedEntity] = flatten(
            [
                observe(e)
                for e in things.expected(area.make(carryable.ContainingMixin).holding)
                if not e.make(mechanics.VisibilityMixin).visible.hard_to_see
                or person.make(mechanics.VisibilityMixin).can_see(e.identity)
            ]
        )
        self.routes: List[movement.AreaRoute] = area.make(
            movement.MovementMixin
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


def observe(entity: Any) -> Sequence[ObservedEntity]:
    if entity.make(mechanics.VisibilityMixin).is_invisible:
        return []
    return [ObservedItem(entity)]


def flatten(l):
    return [item for sl in l for item in sl]
