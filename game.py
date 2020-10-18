from typing import List, Tuple, Dict, Sequence, Optional

import logging
import sys
import time
import inflect
import uuid
import lupa

import crypto
import props
import entity
import behavior

DefaultMoveVerb = "walk"

p = inflect.engine()
scriptEngine = behavior.ScriptEngine()
log = logging.getLogger("dimsum")


class Observable:
    pass


class Event:
    pass


class EventBus:
    async def publish(self, event: Event):
        log.info("publish:%s", event)


class Activity:
    pass


class Kind:
    def __init__(self, identity=None, **kwargs):
        if identity:
            self.identity = identity
        else:
            self.identity = crypto.generate_identity()

    def same(self, other: "Kind"):
        if other is None:
            return False
        return self.identity.public == other.identity.public

    def __str__(self):
        return "kind<%s>" % (self.identity,)

    def __repr__(self):
        return str(self)


class Item(entity.Entity):
    def __init__(self, areas=None, quantity=1, mobility=None, kind=None, **kwargs):
        super().__init__(**kwargs)
        self.areas = areas if areas else {}
        self.mobility = mobility if areas else {}
        self.quantity = quantity
        self.kind = kind if kind else Kind()
        self.validate()

    def link_area(self, new_area, verb=DefaultMoveVerb, **kwargs):
        self.areas[verb] = new_area

    def link_activity(self, name, activity=True):
        self.details.set(name, activity)

    def describes(self, q: str):
        if q.lower() in self.details.name.lower():
            return True
        if q.lower() in str(self).lower():
            return True
        return False

    def observe(self) -> Sequence["ObservedEntity"]:
        return [ObservedEntity(self)]

    def load(self, world, properties):
        super().load(world, properties)
        self.areas = {}
        if "areas" in properties:
            self.areas = {
                key: world.find(value) for key, value in properties["areas"].items()
            }
        if "kind" in properties:
            self.kind = Kind(**properties["kind"])
        if "mobility" in properties:
            self.mobility = properties["mobility"]
        self.quantity = properties["quantity"] if "quantity" else 1

    def accept(self, visitor: entity.EntityVisitor):
        return visitor.item(self)

    def __str__(self):
        if self.quantity > 1:
            return "%d %s" % (self.quantity, p.plural(self.details.name, self.quantity))
        return p.a(self.details.name)

    def __repr__(self):
        return str(self)

    def separate(self, world, player, quantity):
        if quantity < 1:
            raise Exception("too few to separate")

        if quantity > self.quantity:
            raise Exception("too many to separate")

        self.quantity -= quantity

        item = Item(
            creator=player,
            kind=self.kind,
            details=self.details,
            behaviors=self.behaviors,
            quantity=quantity,
        )

        world.register(item)

        return [item]


class IsItemTemplate:
    def apply_item_template(self, **kwargs):
        raise Exception("unimplemented")


class MaybeItem(IsItemTemplate):
    def __init__(self, name: str):
        self.name = name

    def apply_item_template(self, **kwargs):
        return Item(details=props.Details(self.name), **kwargs)


class RecipeItem(IsItemTemplate):
    def __init__(self, recipe: "Recipe"):
        self.recipe = recipe

    def apply_item_template(self, **kwargs):
        return self.recipe.apply_item_template(**kwargs)


class MaybeQuantifiedItem(IsItemTemplate):
    def __init__(self, template: MaybeItem, quantity: float):
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
        self.entity = entity

    def accept(self, visitor):
        return visitor.observed_entity(self)

    def __str__(self):
        return str(self.entity)

    def __repr__(self):
        return str(self)


class ObservedEntities(Observable):
    def __init__(self, entities: List[entity.Entity]):
        self.entities = entities

    def accept(self, visitor):
        return visitor.observed_entities(self)

    def __str__(self):
        return str(p.join(self.entities))

    def __repr__(self):
        return str(self)


class Holding(Activity):
    def __init__(self, item: Item):
        super().__init__()
        self.item = item

    def __str__(self):
        return "holding %s" % (self.item,)

    def __repr__(self):
        return str(self)


class Person(entity.Entity):
    def __init__(self, holding=None, wearing=None, memory=None, **kwargs):
        super().__init__(**kwargs)
        self.holding: List[entity.Entity] = holding if holding else []
        self.wearing: List[entity.Entity] = wearing if wearing else []
        self.memory = memory if memory else {}

    def find(self, q: str):
        for entity in self.holding:
            if entity.describes(q):
                return entity
        for entity in self.wearing:
            if entity.describes(q):
                return entity
        return None

    @property
    def is_invisible(self):
        return "hidden" in self.visible

    def observe(self) -> Sequence["ObservedPerson"]:
        if self.is_invisible:
            return []
        activities = [Holding(e) for e in self.holding if isinstance(e, Item)]
        return [ObservedPerson(self, activities)]

    def describes(self, q: str):
        return q.lower() in self.details.name.lower()

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

    def is_wearing(self, item):
        return item in self.wearing

    def wear(self, item: Item):
        if not self.is_holding(item):
            raise Exception("wear before hold")
        self.drop(item)
        if self.is_holding(item):
            raise Exception("wear before hold")
        self.wearing.append(item)
        item.touch()

    def is_holding(self, item):
        return item in self.holding

    @property
    def items_in_hands(self) -> Sequence[Item]:
        return [e for e in self.holding if isinstance(e, Item)]

    def hold(self, item: Item):
        # See if there's a kind already in inventory.
        for holding in self.items_in_hands:
            if item.kind.same(holding.kind):
                # This will probably need more protection haha
                holding.quantity += item.quantity
                holding.touch()

                # We return, which skips the append to holding below,
                # and that has the effect of obliterating the item we
                # picked up, merging with the one in our hands.
                return holding
        self.holding.append(item)
        item.touch()
        return item

    def remove(self, item: Item):
        if not self.is_wearing(item):
            raise Exception("remove before wear")
        self.hold(item)
        self.wearing.remove(item)
        item.touch()

    def make_visible(self):
        log.info("person:visible")
        self.visible = {}

    def make_invisible(self):
        log.info("person:invisible")
        self.visible = {"hidden": True}

    def consume(self, item):
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
            self.details.map, item.details.map, FoodFields
        )
        log.info("merged %s" % (changes,))
        self.details.update(changes)

    def drop_all(self):
        dropped = []
        while len(self.holding) > 0:
            item = self.holding[0]
            self.drop(item)
            item.touch()
            dropped.append(item)
        return dropped

    def drop(self, item: Item):
        if item in self.holding:
            self.holding.remove(item)
            item.touch()
            return [item]
        return []

    def accept(self, visitor: entity.EntityVisitor):
        return visitor.person(self)

    def __str__(self):
        return self.details.name

    def __repr__(self):
        return str(self)


class ObservedPerson(Observable):
    def __init__(self, person: Person, activities: Sequence[Activity]):
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


class Area(entity.Entity):
    def __init__(self, here=None, **kwargs):
        super().__init__(**kwargs)
        self.here: List[entity.Entity] = here if here else []

    @property
    def items(self) -> List[Item]:
        return [e for e in self.here if isinstance(e, Item)]

    def entities(self) -> List[entity.Entity]:
        return self.here

    def contains(self, e: entity.Entity):
        return e in self.here

    def remove(self, e: entity.Entity):
        self.here.remove(e)
        return self

    def look(self, player: Player):
        people = [
            e.observe() for e in self.here if isinstance(e, Person) and e != player
        ]
        items = [e.observe() for e in self.here if isinstance(e, Item)]
        observed_self = player.observe()[0]
        return AreaObservation(observed_self, self, flatten(people), flatten(items))

    def add_item(self, item: Item):
        for h in self.items:
            if item.kind.same(h.kind):
                h.quantity += item.quantity

                # We return, which skips the append to holding below,
                # and that has the effect of obliterating the item we
                # picked up, merging with the one in our hands.
                return self

        self.here.append(item)
        return self

    def find(self, q: str):
        for entity in self.here:
            if entity.describes(q):
                return entity
        return None

    def accept(self, visitor: entity.EntityVisitor):
        return visitor.area(self)

    def __str__(self):
        return self.details.name

    def __repr__(self):
        return str(self)

    async def entered(self, bus: EventBus, player: Player):
        self.here.append(player)
        await bus.publish(PlayerEnteredArea(player, self))

    async def left(self, bus: EventBus, player: Player):
        self.here.remove(player)
        await bus.publish(PlayerLeftArea(player, self))


class World(entity.Entity):
    def __init__(self, bus: EventBus, wrapping_fn):
        super().__init__()
        self.details = props.Details("World", desc="Ya know, everything")
        self.key = "world"
        self.bus = bus
        self.wrapping_fn = wrapping_fn
        self.entities: Dict[str, entity.Entity] = {}

    def register(self, entity: entity.Entity):
        self.entities[entity.key] = entity

    def unregister(self, entity: entity.Entity):
        del self.entities[entity.key]

    def empty(self):
        return len(self.entities.keys()) == 0

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
            if area.contains(entity):
                return area
        return None

    def find_player_area(self, player: Player):
        area = self.find_entity_area(player)
        return area

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

    def build_new_area(self, player: Player, fromArea: Area, entry: Item):
        log.info("building new area")

        verb = DefaultMoveVerb
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

    def search(self, player: Player, whereQ: str, **kwargs):
        area = self.find_player_area(player)

        order = [player.find, area.find]

        if "unheld" in kwargs:
            order = [area.find, player.find]

        for fn in order:
            item = fn(whereQ)
            if item:
                return item

        return None

    async def perform(self, player: Player, action):
        area = self.find_player_area(player)
        ctx = Ctx(self.wrapping_fn, world=self, person=player, area=area)
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
                    self.wrapping_fn, world=self, area=area, entity=entity, **kwargs
                )
                await ctx.hook(name)

    def __str__(self):
        return "$world"

    def __repr__(self):
        return "$world"


class HooksAround:
    def __enter__(self):
        return None

    def __exit__(self, type, value, traceback):
        pass


class Ctx:
    def __init__(self, wrapping_fn, world=None, person=None, **kwargs):
        self.se = scriptEngine
        self.wrapping_fn = wrapping_fn
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
        found = []
        entities = self.entities()
        log.info("hook:%s %s" % (name, entities))
        for entity in entities:
            behaviors = entity.get_behaviors(name)
            if len(behaviors) > 0:
                log.info(
                    "hook:%s invoke '%s' %d behavior" % (name, entity, len(behaviors))
                )
            found.extend(behaviors)

        scope = self.scope
        prepared = self.se.prepare(scope, self.wrapping_fn)
        for b in found:
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
        pass


class PersonAction(Action):
    async def perform(self, ctx: Ctx, world: World, player: Player):
        raise Exception("unimplemented")


class PlayerJoined(Event):
    def __init__(self, player: Player):
        self.player = player

    def __str__(self):
        return "%s joined" % (self.player)


class PlayerQuit(Event):
    def __init__(self, player: Player):
        self.player = player

    def __str__(self):
        return "%s quit" % (self.player)


class AreaConstructed(Event):
    def __init__(self, player: Player, area: Area):
        self.player = player
        self.area = area

    def __str__(self):
        return "%s constructed %s" % (self.player, self.area)


class PlayerEnteredArea(Event):
    def __init__(self, player: Player, area: Area):
        self.player = player
        self.area = area

    def __str__(self):
        return "%s entered %s" % (self.player, self.area)


class PlayerLeftArea(Event):
    def __init__(self, player: Player, area: Area):
        self.player = player
        self.area = area

    def __str__(self):
        return "%s left %s" % (self.player, self.area)


class ItemHeld(Event):
    def __init__(self, player: Player, area: Area, item: Item):
        self.player = player
        self.area = area
        self.item = item

    def __str__(self):
        return "%s picked up %s" % (self.player, self.item)


class ItemMade(Event):
    def __init__(self, player: Player, area: Area, item: Item):
        self.player = player
        self.area = area
        self.item = item

    def __str__(self):
        return "%s created %s out of thin air!" % (self.player, self.item)


class ItemEaten(Event):
    def __init__(self, player: Player, area: Area, item: Item):
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
        self.player = player
        self.area = area
        self.items = items

    def __str__(self):
        return "%s dropped %s" % (self.player, p.join(self.items))


class ItemObliterated(Event):
    def __init__(self, player: Player, area: Area, item: Item):
        self.player = player
        self.area = area
        self.item = item

    def __str__(self):
        return "%s obliterated %s" % (self.player, self.item)


def flatten(l):
    return [item for sl in l for item in sl]
