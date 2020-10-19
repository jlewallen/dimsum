from typing import List, Tuple, Dict, Sequence, Optional

import logging
import sys
import enum
import time
import inflect
import abc
import lupa

import crypto
import props
import entity
import behavior

import occupyable
import carryable

DefaultMoveVerb = "walk"

p = inflect.engine()
scriptEngine = behavior.ScriptEngine()
log = logging.getLogger("dimsum")


class Observable:
    pass


class Event:
    pass


class Wearable:
    @abc.abstractmethod
    def touch(self):
        pass


class EventBus:
    async def publish(self, event: Event):
        log.info("publish:%s", event)


class Activity:
    pass


class HasRoutesMixin:
    def __init__(self, areas=None, **kwargs):
        super().__init__()
        self.areas = areas if areas else {}

    def link_area(self, new_area, verb=DefaultMoveVerb, **kwargs):
        self.areas[verb] = new_area


class InteractableMixin:
    def __init__(self, interactions=None, **kwargs):
        super().__init__(**kwargs)
        self.interactions = interactions if interactions else {}

    def link_activity(self, name: str, activity=True):
        self.interactions[name] = activity

    def when_activity(self, name: str):
        return self.interactions[name] if name in self.interactions else False

    def when_worn(self):
        return self.when_activity(props.Worn)

    def when_eaten(self):
        return self.when_activity(props.Eaten)

    def when_opened(self):
        return self.when_activity(props.Opened)

    def when_drank(self):
        return self.when_activity(props.Drank)


class VisibilityMixin:
    def __init__(self, visible=None, **kwargs):
        super().__init__(**kwargs)

    def make_visible(self):
        log.info("person:visible")
        self.visible = {}

    def make_invisible(self):
        log.info("person:invisible")
        self.visible = {"hidden": True}

    @property
    def is_invisible(self):
        return "hidden" in self.visible


class AreaRoute:
    def go(self) -> None:
        pass

    def available(self) -> bool:
        return False

    def satisfies(self, **kwargs) -> bool:
        return False


class MovementMixin:
    def __init__(self, routes=None, **kwargs):
        super().__init__(**kwargs)
        self.routes: List[AreaRoute] = routes if routes else []

    def find_route(self, **kwargs) -> Optional[AreaRoute]:
        log.info("find-route: %s %s", kwargs, self.routes)
        for r in self.routes:
            if r.satisfies(**kwargs):
                log.info("f")
                return r
        return None

    def add_route(self, route: AreaRoute) -> AreaRoute:
        self.routes.append(route)
        return route


class EdibleMixin:
    def consumed(self, player):
        FoodFields = [
            props.SumFields("sugar"),
            props.SumFields("fat"),
            props.SumFields("protein"),
            props.SumFields("toxicity"),
            props.SumFields("caffeine"),
            props.SumFields("alcohol"),
            props.SumFields("nutrition"),
            props.SumFields("vitamins"),
        ]
        changes = props.merge_dictionaries(
            player.details.map, self.details.map, FoodFields
        )
        log.info("merged %s" % (changes,))
        player.details.update(changes)


class Item(
    entity.Entity,
    Wearable,
    carryable.CarryableMixin,
    HasRoutesMixin,
    InteractableMixin,
    MovementMixin,
    VisibilityMixin,
    EdibleMixin,
):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.validate()

    def describes(self, q: str):
        if q.lower() in self.details.name.lower():
            return True
        if q.lower() in str(self).lower():
            return True
        return False

    def separate(self, world, player, quantity):
        self.decrease_quantity(quantity)
        item = Item(
            creator=player,
            kind=self.kind,
            details=self.details,
            behaviors=self.behaviors,
            quantity=quantity,
        )
        # TODO Move to caller
        world.register(item)
        return [item]

    def observe(self) -> Sequence["ObservedEntity"]:
        return [ObservedEntity(self)]

    def accept(self, visitor: entity.EntityVisitor):
        return visitor.item(self)

    def __str__(self):
        if self.quantity > 1:
            return "%d %s" % (self.quantity, p.plural(self.details.name, self.quantity))
        return p.a(self.details.name)

    def __repr__(self):
        return str(self)


class ApparalMixin:
    def __init__(self, wearing=None, **kwargs):
        super().__init__(**kwargs)
        self.wearing = wearing if wearing else []

    def is_wearing(self, item: Wearable) -> bool:
        return item in self.wearing

    def wear(self, item: Wearable):
        if not self.is_holding(item):
            raise Exception("wear before hold")
        self.drop(item)
        if self.is_holding(item):
            raise Exception("wear before hold")
        self.wearing.append(item)
        item.touch()

    def unwear(self, item: Wearable, **kwargs):
        if not self.is_wearing(item):
            raise Exception("remove before wear")
        self.hold(item)
        self.wearing.remove(item)
        item.touch()


class Direction(enum.Enum):
    NORTH = 1
    SOUTH = 2
    WEST = 3
    EAST = 4


class FindsRoute:
    async def find(self, world, player, verb=DefaultMoveVerb):
        raise Exception("unimplemented")


class FindDirectionalRoute(FindsRoute):
    def __init__(self, direction: Direction):
        super().__init__()
        self.direction = direction

    async def find(self, world, player, **kwargs):
        area = world.find_player_area(player)
        route = area.find_route(direction=self.direction)
        if route:
            return route.area
        return None


class FindNamedRoute(FindsRoute):
    def __init__(self, name: str):
        super().__init__()
        self.name = name

    async def find(self, world, player, verb=DefaultMoveVerb):
        item = world.search(player, self.name)
        if item is None:
            log.info("no named route: %s", self.name)
            return None

        log.info("found named route: %s = %s", self.name, item)

        # If the person owns this item and they try to go the thing,
        # this is how new areas area created, one of them.
        have_verb = verb in item.areas
        if not have_verb:
            area = world.find_player_area(player)
            new_area = world.build_new_area(player, area, item, verb=verb)
            item.link_area(new_area, verb=verb)

        destination = item.areas[verb]

        player.drop_here(world, item=item)

        return destination


class DirectionalRoute(AreaRoute):
    def __init__(self, direction: Direction = None, area: "Area" = None):
        super().__init__()
        if direction is None:
            raise Exception("direction is required")
        self.direction = direction
        if area is None:
            raise Exception("area is required")
        self.area = area

    def satisfies(self, direction=None, **kwargs) -> bool:
        log.info("%s %s", direction, self.direction)
        return self.direction == direction


class IsItemTemplate:
    def apply_item_template(self, **kwargs):
        raise Exception("unimplemented")


class MaybeItem(IsItemTemplate):
    def __init__(self, name: str):
        super().__init__()
        self.name = name

    def apply_item_template(self, **kwargs):
        return Item(details=props.Details(self.name), **kwargs)


class RecipeItem(IsItemTemplate):
    def __init__(self, recipe: "Recipe"):
        super().__init__()
        self.recipe = recipe

    def apply_item_template(self, **kwargs):
        return self.recipe.apply_item_template(**kwargs)


class MaybeQuantifiedItem(IsItemTemplate):
    def __init__(self, template: MaybeItem, quantity: float):
        super().__init__()
        self.template = template
        self.quantity = quantity

    def apply_item_template(self, **kwargs):
        return self.template.apply_item_template(quantity=self.quantity, **kwargs)


class Recipe(Item):
    def __init__(self, required=None, base=None, **kwargs):
        super().__init__(**kwargs)
        self.required = required if required else {}
        self.base = base if base else {}
        self.validate()

    def accept(self, visitor: entity.EntityVisitor):
        return visitor.recipe(self)

    def apply_item_template(self, **kwargs):
        # TODO Also sign with the recipe
        return Item(
            details=props.Details.from_base(self.base), kind=self.kind, **kwargs
        )


class ObservedEntity(Observable):
    def __init__(self, entity: entity.Entity):
        super().__init__()
        self.entity = entity

    def accept(self, visitor):
        return visitor.observed_entity(self)

    def __str__(self):
        return str(self.entity)

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


class HoldingActivity(Activity):
    def __init__(self, item: Item):
        super().__init__()
        self.item = item

    def __str__(self):
        return "holding %s" % (self.item,)

    def __repr__(self):
        return str(self)


class MemoryMixin:
    def __init__(self, memory=None, **kwargs):
        super().__init__()
        self.memory = memory if memory else {}

    def find_memory(self, q: str):
        for name, entity in self.memory.items():
            if q.lower() in name.lower():
                return entity
        for name, entity in self.memory.items():
            if entity.describes(q):
                return entity
        return None

    def find_recipe(self, q: str):
        for name, entity in self.memory.items():
            if name.startswith("r:"):
                name = name.replace("r:", "")
                if q.lower() in name.lower():
                    return entity
        return None


class LivingCreature(
    entity.Entity,
    occupyable.Living,
    carryable.CarryingMixin,
    ApparalMixin,
    VisibilityMixin,
    MemoryMixin,
):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @property
    def quantity(self):
        return 1


class Animal(LivingCreature):
    pass


class Person(LivingCreature):
    def find(self, q: str):
        for entity in self.holding:
            if entity.describes(q):
                return entity
        for entity in self.wearing:
            if entity.describes(q):
                return entity
        return None

    def observe(self) -> Sequence["ObservedPerson"]:
        if self.is_invisible:
            return []
        activities = [HoldingActivity(e) for e in self.holding if isinstance(e, Item)]
        return [ObservedPerson(self, activities)]

    def describes(self, q: str):
        return q.lower() in self.details.name.lower()

    def accept(self, visitor: entity.EntityVisitor):
        return visitor.person(self)

    def __str__(self):
        return self.details.name

    def __repr__(self):
        return str(self)


class ObservedPerson(Observable):
    def __init__(self, person: Person, activities: Sequence[Activity]):
        super().__init__()
        self.person = person
        self.activities = activities

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


class Player(Person):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


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


class PersonalObservation(Observation):
    def __init__(self, who: ObservedPerson):
        super().__init__()
        self.who = who

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
    def __init__(self, person: ObservedPerson, item: ObservedEntity):
        super().__init__()
        self.person = person
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
        return "%s observes %s" % (
            self.person,
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
    def __init__(
        self,
        who: ObservedPerson,
        where: entity.Entity,
        people: List[ObservedPerson],
        items: List[ObservedEntity],
    ):
        super().__init__()
        self.who = who
        self.where = where
        self.people = people
        self.items = items

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


class Area(
    entity.Entity, carryable.ContainingMixin, occupyable.OccupyableMixin, MovementMixin
):
    def __init__(self, routes=None, **kwargs):
        super().__init__(**kwargs)

    def entities(self) -> List[entity.Entity]:
        return flatten([self.holding, self.occupied])

    def look(self, player: Player):
        people = [e.observe() for e in self.occupied if e != player]
        items = [e.observe() for e in self.holding if e]
        observed_self = player.observe()[0]
        return AreaObservation(observed_self, self, flatten(people), flatten(items))

    def entities_named(self, of: str):
        return [e for e in self.entities() if e.describes(of)]

    def entities_of_kind(self, kind: entity.Kind):
        return [e for e in self.entities() if e.kind and e.kind.same(kind)]

    def number_of_named(self, of: str) -> int:
        return sum([e.quantity for e in self.entities_named(of)])

    def number_of_kind(self, kind: entity.Kind) -> int:
        return sum([e.quantity for e in self.entities_of_kind(kind)])

    def accept(self, visitor: entity.EntityVisitor):
        return visitor.area(self)

    def __str__(self):
        return self.details.name

    def __repr__(self):
        return str(self)


class World(entity.Entity):
    def __init__(self, bus: EventBus, context_factory):
        super().__init__()
        self.details = props.Details("World", desc="Ya know, everything")
        self.key = "world"
        self.bus = bus
        self.context_factory = context_factory
        self.entities: Dict[str, entity.Entity] = {}
        self.destroyed: Dict[str, entity.Entity] = {}

    def register(self, entity: entity.Entity):
        self.entities[entity.key] = entity

    def unregister(self, entity: entity.Entity):
        entity.destroy()
        del self.entities[entity.key]
        self.destroyed[entity.key] = entity

    def empty(self):
        return len(self.entities.keys()) == 0

    def items(self):
        return [e for e in self.entities.values() if isinstance(e, Item)]

    def areas(self):
        return [e for e in self.entities.values() if isinstance(e, Area)]

    def people(self):
        return [e for e in self.entities.values() if isinstance(e, Person)]

    def players(self):
        return [e for e in self.entities.values() if isinstance(e, Player)]

    def find_person_by_name(self, name):
        for person in self.people():
            if person.details.name == name:
                return person
        return None

    def welcome_area(self):
        return self.areas()[0]

    def look(self, player: Player):
        area = self.find_player_area(player)
        return area.look(player)

    def find_entity_area(self, entity: entity.Entity):
        for area in self.areas():
            if area.contains(entity) or area.occupying(entity):
                return area
        return None

    def find_player_area(self, player: Player):
        return self.find_entity_area(player)

    def contains(self, key):
        return key in self.entities

    def find(self, key):
        return self.entities[key]

    def resolve(self, keys):
        return [self.entities[key] for key in keys]

    def add_area(self, area: Area):
        self.register(area)
        for entity in area.entities():
            self.register(entity)

    def build_new_area(
        self, player: Player, fromArea: Area, entry: Item, verb: str = DefaultMoveVerb
    ):
        log.info("building new area")

        theWayBack = Item(creator=player, details=entry.details.clone())
        theWayBack.link_area(fromArea, verb=verb)

        area = Area(
            creator=player,
            details=props.Details(
                "A pristine, new place.",
                desc="Nothing seems to be here, maybe you should decorate?",
            ),
        )
        area.add_item(theWayBack)
        self.add_area(area)
        return area

    def search_hands(self, player: Player, whereQ: str):
        return player.find(whereQ)

    def search_floor(self, player: Player, whereQ: str):
        area = self.find_player_area(player)
        return area.find(whereQ)

    def search(self, player: Player, whereQ: str, unheld=None, **kwargs):
        log.info("%s", player)
        area = self.find_player_area(player)
        log.info("%s", area)

        order = [player.find, area.find]

        if unheld:
            order = [area.find, player.find]

        for fn in order:
            item = fn(whereQ)
            if item:
                return item

        return None

    async def perform(self, player: Player, action):
        area = self.find_player_area(player)
        ctx = Ctx(self.context_factory, world=self, person=player, area=area)
        return await action.perform(ctx, self, player)

    async def tick(self, now: Optional[float] = None):
        if now is None:
            now = time.time()
        return await self.everywhere("tick", time=now)

    async def everywhere(self, name: str, **kwargs):
        log.info("everywhere:%s %s", name, kwargs)
        everything = list(self.entities.values())
        for entity in everything:
            behaviors = entity.get_behaviors(name)
            if len(behaviors) > 0:
                log.info("tick: %s", entity)
                area = self.find_entity_area(entity)
                ctx = Ctx(
                    self.context_factory, world=self, area=area, entity=entity, **kwargs
                )
                await ctx.hook(name)

    def __str__(self):
        return "$world"

    def __repr__(self):
        return "$world"


class Ctx:
    # This should eventually get worked out. Just return Ctx from this function?
    def __init__(self, context_factory, world=None, person=None, **kwargs):
        super().__init__()
        self.se = scriptEngine
        self.context_factory = context_factory
        self.world = world
        self.person = person
        self.scope = behavior.Scope(world=world, person=person, **kwargs)

    def extend(self, **kwargs):
        self.scope = self.scope.extend(**kwargs)
        return self

    def entities(self):
        def get_entities_inside(array):
            return flatten([get_entities(e) for e in array])

        def get_entities(thing):
            if isinstance(thing, entity.Entity):
                return [thing]
            if isinstance(thing, list):
                return get_entities_inside(thing)
            return []

        return get_entities_inside(self.scope.values())

    async def hook(self, name):
        found = {}
        entities = self.entities()
        log.info("hook:%s %s" % (name, entities))
        for entity in entities:
            behaviors = entity.get_behaviors(name)
            if len(behaviors) > 0:
                log.info(
                    "hook:%s invoke '%s' %d behavior" % (name, entity, len(behaviors))
                )
            found[entity] = behaviors

        scope = self.scope
        for entity, behaviors in found.items():

            def create_context():
                return self.context_factory(creator=entity)

            for b in behaviors:
                prepared = self.se.prepare(scope, create_context)
                thunk = behavior.GenericThunk
                if "person" in scope.map and scope.map["person"]:
                    thunk = behavior.PersonThunk
                actions = self.se.execute(thunk, prepared, b)
                if actions:
                    for action in actions:
                        await self.world.perform(self.person, action)
                        log.info("performing: %s", action)


class Action:
    def __init__(self, **kwargs):
        super().__init__()


class PersonAction(Action):
    async def perform(self, ctx: Ctx, world: World, player: Player):
        raise Exception("unimplemented")


class PlayerJoined(Event):
    def __init__(self, player: Player):
        super().__init__()
        self.player = player

    def __str__(self):
        return "%s joined" % (self.player)


class PlayerQuit(Event):
    def __init__(self, player: Player):
        super().__init__()
        self.player = player

    def __str__(self):
        return "%s quit" % (self.player)


class AreaConstructed(Event):
    def __init__(self, player: Player, area: Area):
        super().__init__()
        self.player = player
        self.area = area

    def __str__(self):
        return "%s constructed %s" % (self.player, self.area)


class ItemHeld(Event):
    def __init__(self, player: Player, area: Area, item: Item):
        super().__init__()
        self.player = player
        self.area = area
        self.item = item

    def __str__(self):
        return "%s picked up %s" % (self.player, self.item)


class ItemMade(Event):
    def __init__(self, player: Player, area: Area, item: Item):
        super().__init__()
        self.player = player
        self.area = area
        self.item = item

    def __str__(self):
        return "%s created %s out of thin air!" % (self.player, self.item)


class ItemEaten(Event):
    def __init__(self, player: Player, area: Area, item: Item):
        super().__init__()
        self.player = player
        self.area = area
        self.item = item

    def __str__(self):
        return "%s just ate %s!" % (self.player, self.item)


class ItemDrank(Event):
    def __init__(self, player: Player, area: Area, item: Item):
        self.player = player
        self.area = area
        self.item = item

    def __str__(self):
        return "%s just drank %s!" % (self.player, self.item)


class ItemsDropped(Event):
    def __init__(self, player: Player, area: Area, items: List[Item]):
        super().__init__()
        self.player = player
        self.area = area
        self.items = items

    def __str__(self):
        return "%s dropped %s" % (self.player, p.join(self.items))


class ItemObliterated(Event):
    def __init__(self, player: Player, area: Area, item: Item):
        super().__init__()
        self.player = player
        self.area = area
        self.item = item

    def __str__(self):
        return "%s obliterated %s" % (self.player, self.item)


def flatten(l):
    return [item for sl in l for item in sl]


def remove_nones(l):
    return [e for e in l if e]
