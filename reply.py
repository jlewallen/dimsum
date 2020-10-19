from typing import List, Sequence, Any
import inflect
import entity
import game

p = inflect.engine()


class Observable:
    pass


class Reply:
    def accept(self, visitor):
        raise Error("unimplemented")


class SimpleReply(Reply):
    def __init__(self, message: str, **kwargs):
        super().__init__()
        self.message = message
        self.item = kwargs["item"] if "item" in kwargs else None


class Success(SimpleReply):
    def accept(self, visitor):
        return visitor.success(self)

    def __str__(self):
        return "Success<%s>" % (self.message,)


class Failure(SimpleReply):
    def accept(self, visitor):
        return visitor.failure(self)

    def __str__(self):
        return "Failure<%s>" % (self.message,)


class Observation(Reply, Observable):
    pass


class ObservedEntity(Observable):
    pass


class ObservedItem(ObservedEntity):
    def __init__(self, item: game.Item):
        super().__init__()
        self.item = item

    def accept(self, visitor):
        return visitor.observed_entity(self)

    def __str__(self):
        return str(self.item)

    def __repr__(self):
        return str(self)


class ObservedAnimal(ObservedEntity):
    def __init__(self, animal: game.Animal):
        super().__init__()
        self.animal = animal

    def accept(self, visitor):
        return visitor.observed_person(self)

    def __str__(self):
        return "%s" % (self.animal,)

    def __repr__(self):
        return str(self)


class ObservedPerson(ObservedEntity):
    def __init__(self, person: game.Person):
        super().__init__()
        self.person = person
        activities = [game.HoldingActivity(e) for e in person.holding]
        self.activities: Sequence[game.Activity] = activities

    @property
    def holding(self):
        return self.person.holding

    @property
    def memory(self):
        return self.person.memory

    def accept(self, visitor):
        return visitor.observed_person(self)

    def __str__(self):
        if len(self.activities) == 0:
            return "%s" % (self.person,)
        return "%s who is %s" % (self.person, p.join(list(map(str, self.activities))))

    def __repr__(self):
        return str(self)


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
    def __init__(self, who: game.Person):
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
    def __init__(self, entities: List[entity.Entity]):
        super().__init__()
        self.entities = entities

    def accept(self, visitor):
        return visitor.entities_observation(self)

    def __str__(self):
        return "observed %s" % (p.join(self.entities),)


class AreaObservation(Observation):
    def __init__(self, area: game.Area, person: game.Person):
        super().__init__()
        self.who: ObservedPerson = ObservedPerson(person)
        self.where: game.Area = area
        self.people: List[ObservedPerson] = flatten(
            [observe(e) for e in area.occupied if e != person]
        )
        self.items: List[ObservedEntity] = flatten(
            [observe(e) for e in area.holding if e]
        )

    @property
    def details(self):
        return self.where.details

    def accept(self, visitor):
        return visitor.area_observation(self)

    def __str__(self):
        return "%s observes %s, also here %s and visible is %s" % (
            self.who,
            self.details,
            self.people,
            self.items,
        )


def observe(entity: Any) -> Sequence[ObservedEntity]:
    if isinstance(entity, game.Person):
        if entity.is_invisible:
            return []
        return [ObservedPerson(entity)]
    if isinstance(entity, game.Animal):
        if entity.is_invisible:
            return []
        return [ObservedAnimal(entity)]
    if isinstance(entity, game.Item):
        return [ObservedItem(entity)]
    raise Exception("unexpected observation target: %s" % (entity,))


def flatten(l):
    return [item for sl in l for item in sl]
