from typing import Sequence
import logging
import lupa

import properties
import kinds
import entity
import game
import things
import envo
import world
import living
import actions
import finders
import mechanics
import carryable

log = logging.getLogger("dimsum")


def context_factory(**kwargs):
    return LupaContext(**kwargs)


class LupaContext:
    def __init__(self, creator=None):
        self.creator = creator

    def wrap(self, thing):
        if thing is None:
            return None
        if isinstance(thing, list):
            return [self.wrap(e) for e in thing]
        if isinstance(thing, dict):
            return {key: self.wrap(value) for key, value in thing.items()}
        if isinstance(thing, world.World):
            return LupaWorld(self, thing)
        if isinstance(thing, envo.Area):
            return LupaArea(self, thing)
        if isinstance(thing, things.Item):
            return LupaItem(self, thing)
        return LupaItem(self, thing)


class LupaEntity:
    def __init__(self, ctx: LupaContext, entity: entity.Entity):
        self.entity = entity
        self.ctx = ctx

    def unlua(self, value):
        if lupa.lua_type(value) == "table":
            v = {}
            for key, val in value.items():
                v[key] = val
            return v
        return value

    def __setitem__(self, key: str, value):
        log.info(
            "entity:entity s: %s %s=%s (%s)"
            % (str(self), str(key), str(value), lupa.lua_type(value))
        )
        self.entity.props[key] = self.unlua(value)

    def __getitem__(self, key: str):
        log.info("entity:entity g: %s %s" % (str(self), str(key)))
        if key in self.entity.props.keys:
            return self.entity.props[key]
        if hasattr(self, key):
            return getattr(self, key)
        if hasattr(self.entity, key):
            return getattr(self.entity, key)
        return None

    def make_item_from_table(self, table, **kwargs) -> things.Item:
        log.info(
            "area:make: %s",
            ", ".join(["%s=%s" % (key, value) for key, value in table.items()]),
        )

        kind = table["kind"] if "kind" in table else kinds.Kind()
        del table["kind"]

        quantity = table["quantity"] if "quantity" in table else 1
        del table["quantity"]

        props = properties.Common(name=table.name)
        del table["name"]

        for key, value in table.items():
            props.map[key] = value

        item = things.Item(props=props, **kwargs)
        if kind:
            with item.make(carryable.CarryableMixin) as carry:
                carry.kind = kind
                carry.quantity = quantity
        return item


class LupaWorld(LupaEntity):
    @property
    def world(self) -> world.World:
        assert isinstance(self.entity, world.World)
        return self.entity


class LupaArea(LupaEntity):
    @property
    def area(self) -> envo.Area:
        assert isinstance(self.entity, envo.Area)
        return self.entity

    def number(self, of):
        with self.area.make(carryable.ContainingMixin) as contain:
            if isinstance(of, str):
                return contain.number_of_named(of)
            return contain.number_of_kind(of)

    def make(self, table):
        item = self.make_item_from_table(table, creator=self.ctx.creator)
        return [actions.AddItemArea(area=self.area, item=item)]


class LupaItem(LupaEntity):
    @property
    def item(self) -> things.Item:
        assert isinstance(self.entity, things.Item)
        return self.entity

    def kind(self, name: str) -> kinds.Kind:
        return self.entity.get_kind(name)

    def visible(self):
        with self.entity.make(mechanics.VisibilityMixin) as vis:
            vis.make_visible()

    def invisible(self):
        with self.entity.make(mechanics.VisibilityMixin) as vis:
            vis.make_invisible()

    def is_invisible(self):
        return self.entity.make(mechanics.VisibilityMixin).is_invisible

    def go(self, area) -> Sequence[game.Action]:
        return [actions.Go(area=area)]

    def make(self, table) -> Sequence[game.Action]:
        item = self.make_item_from_table(table, creator=self.entity)
        return [actions.Make(item=finders.StaticItem(item=item))]
