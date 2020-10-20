from typing import List, Tuple, Dict, Sequence, Optional, Any, cast
import logging
import inflect
import copy
import abc

import crypto
import props
import entity
import behavior
import mechanics
import occupyable
import carryable
import health
import movement
import apparel

p = inflect.engine()
log = logging.getLogger("dimsum")


class Event:
    pass


class Item(
    entity.Entity,
    apparel.Wearable,
    carryable.CarryableMixin,
    mechanics.InteractableMixin,
    movement.MovementMixin,
    mechanics.VisibilityMixin,
    health.EdibleMixin,
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
    def __init__(self, template=None, **kwargs):
        super().__init__(**kwargs)
        assert template
        self.template = template.clone()

    def create_item(self, **kwargs) -> Item:
        # TODO Also sign with the recipe
        log.info("recipe:creating %s %s", self.template, kwargs)
        return self.template.clone(**kwargs)

    def accept(self, visitor: entity.EntityVisitor) -> Any:
        return visitor.recipe(self)


class Action:
    def __init__(self, **kwargs):
        super().__init__()


from living import *
from area import *


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


def remove_nones(l):
    return [e for e in l if e]
