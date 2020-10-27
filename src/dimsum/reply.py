from typing import List, Sequence, Any
import logging
import inflect
import entity
import game
import things
import envo
import living
import animals
import movement

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
    def __init__(self, alive: living.Alive):
        super().__init__()
        self.alive = alive
        self.activities: Sequence[living.Activity] = [
            living.HoldingActivity(e) for e in things.expected(alive.holding)
        ]

    @property
    def holding(self):
        return self.alive.holding

    @property
    def memory(self):
        return self.alive.memory

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
    def __init__(self, who: animals.Person):
        super().__init__()
        self.who = ObservedPerson(who)

    @property
    def details(self):
        return self.who.person.details

    @property
    def properties(self):
        return self.details.map

    @property
    def memory(self):
        return self.who.memory

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
    def details(self):
        return self.item.details

    @property
    def properties(self):
        return self.details.map

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

    def accept(self, visitor):
        return visitor.entities_observation(self)

    def __str__(self):
        return "observed %s" % (p.join(self.entities),)


class AreaObservation(Observation):
    def __init__(self, area: envo.Area, person: animals.Person):
        super().__init__()
        assert area
        assert person
        self.who: ObservedPerson = ObservedPerson(person)
        self.where: envo.Area = area
        self.living: List[ObservedLiving] = flatten(
            [observe(e) for e in area.occupied if e != person]
        )
        self.items: List[ObservedEntity] = flatten(
            [observe(e) for e in area.holding if e]
        )
        self.routes: List[movement.AreaRoute] = area.routes

    @property
    def details(self):
        return self.where.details

    def accept(self, visitor):
        return visitor.area_observation(self)

    def __str__(self):
        return "%s observes %s, also here %s and visible is %s" % (
            self.who,
            self.details,
            self.living,
            self.items,
        )


def observe(entity: Any) -> Sequence[ObservedEntity]:
    if isinstance(entity, animals.Person):
        if entity.is_invisible:
            return []
        return [ObservedPerson(entity)]
    if isinstance(entity, animals.Animal):
        if entity.is_invisible:
            return []
        return [ObservedAnimal(entity)]
    if isinstance(entity, things.Item):
        return [ObservedItem(entity)]
    raise Exception("unexpected observation target: %s" % (entity,))


def flatten(l):
    return [item for sl in l for item in sl]
