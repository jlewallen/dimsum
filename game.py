from typing import List, Tuple, Dict, Sequence, Optional, Any, cast
import logging
import inflect
import abc

import crypto
import props
import entity
import behavior
import mechanics
import occupyable
import carryable
import edible
import movement
import apparel

p = inflect.engine()
log = logging.getLogger("dimsum")


class Event:
    pass


class Activity:
    pass


class Item(
    entity.Entity,
    apparel.Wearable,
    carryable.CarryableMixin,
    mechanics.InteractableMixin,
    movement.MovementMixin,
    mechanics.VisibilityMixin,
    edible.EdibleMixin,
):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.validate()

    def describes(self, q: str) -> bool:
        if q.lower() in self.details.name.lower():
            return True
        if q.lower() in str(self).lower():
            return True
        return False

    def separate(
        self, quantity: int, registrar: entity.Registrar = None, **kwargs
    ) -> List["Item"]:
        assert registrar
        self.decrease_quantity(quantity)
        item = Item(
            kind=self.kind,
            details=self.details,
            behaviors=self.behaviors,
            quantity=quantity,
            **kwargs
        )
        # TODO Move to caller
        registrar.register(item)
        return [item]

    def accept(self, visitor: entity.EntityVisitor) -> Any:
        return visitor.item(self)

    def __str__(self):
        if self.quantity > 1:
            return "%d %s" % (self.quantity, p.plural(self.details.name, self.quantity))
        return p.a(self.details.name)

    def __repr__(self):
        return str(self)


class ItemFactory:
    def create_item(self, **kwargs) -> Item:
        raise Exception("unimplemented")


class MaybeItem(ItemFactory):
    def __init__(self, name: str):
        super().__init__()
        self.name = name

    def create_item(self, **kwargs) -> Item:
        return Item(details=props.Details(self.name), **kwargs)


class RecipeItem(ItemFactory):
    def __init__(self, recipe: "Recipe"):
        super().__init__()
        self.recipe = recipe

    def create_item(self, **kwargs) -> Item:
        return self.recipe.create_item(**kwargs)


class MaybeQuantifiedItem(ItemFactory):
    def __init__(self, template: MaybeItem, quantity: float):
        super().__init__()
        self.template: MaybeItem = template
        self.quantity: float = quantity

    def create_item(self, **kwargs) -> Item:
        return self.template.create_item(quantity=self.quantity, **kwargs)


class Recipe(Item, ItemFactory, mechanics.Memorable):
    def __init__(self, required=None, base=None, **kwargs):
        super().__init__(**kwargs)
        self.required = required if required else {}
        self.base = base if base else {}
        self.validate()

    def accept(self, visitor: entity.EntityVisitor):
        return visitor.recipe(self)

    def create_item(self, **kwargs):
        # TODO Also sign with the recipe
        return Item(
            details=props.Details.from_base(self.base), kind=self.kind, **kwargs
        )


class HoldingActivity(Activity):
    def __init__(self, item: Item):
        super().__init__()
        self.item = item

    def __str__(self):
        return "holding %s" % (self.item,)

    def __repr__(self):
        return str(self)


class LivingCreature(
    entity.Entity,
    occupyable.Living,
    carryable.CarryingMixin,
    apparel.ApparelMixin,
    mechanics.VisibilityMixin,
    mechanics.MemoryMixin,
):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @property
    def quantity(self):
        return 1

    def describes(self, q: str) -> bool:
        return q.lower() in self.details.name.lower()

    def find(self, q: str) -> Optional[carryable.CarryableMixin]:
        for e in self.holding:
            if e.describes(q):
                return e
        for e in self.wearing:
            if e.describes(q):
                return e
        return None

    def __str__(self):
        return self.details.name

    def __repr__(self):
        return str(self)


class Animal(LivingCreature):
    def accept(self, visitor: entity.EntityVisitor):
        return visitor.animal(self)


class Person(LivingCreature):
    def accept(self, visitor: entity.EntityVisitor):
        return visitor.person(self)


class Player(Person):
    pass


class Area(
    entity.Entity,
    carryable.ContainingMixin,
    occupyable.OccupyableMixin,
    movement.MovementMixin,
    movement.Area,
    mechanics.Memorable,
):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @property
    def items(self):
        return self.holding

    def entities(self) -> List[entity.Entity]:
        return flatten([self.holding, self.occupied])

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


class Action:
    def __init__(self, **kwargs):
        super().__init__()


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
