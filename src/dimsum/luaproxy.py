from typing import Sequence
import logging
import lupa

import model.properties as properties
import model.kinds as kinds
import model.entity as entity
import model.game as game
import model.world as world
import model.finders as finders

import model.scopes.mechanics as mechanics
import model.scopes.carryable as carryable
import model.scopes as scopes

import plugins.default.actions as actions
import plugins.creation as creation

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

    def make_item_from_table(self, table, **kwargs) -> entity.Entity:
        log.info(
            "area:make: %s",
            ", ".join(["%s=%s" % (key, value) for key, value in table.items()]),
        )

        kind = (
            table["kind"]
            if "kind" in table
            else kinds.Kind(identity=entity.generate_identity())
        )
        del table["kind"]

        quantity = table["quantity"] if "quantity" in table else 1
        del table["quantity"]

        props = properties.Common(name=table.name)
        del table["name"]

        for key, value in table.items():
            props.map[key] = value

        item = scopes.item(props=props, **kwargs)
        if kind:
            with item.make(carryable.Carryable) as carry:
                carry.kind = kind
                carry.quantity = quantity
        return item


class LupaWorld(LupaEntity):
    @property
    def world(self) -> world.World:
        assert isinstance(self.entity, world.World)
        return self.entity


class LupaItem(LupaEntity):
    @property
    def area(self) -> entity.Entity:
        return self.entity

    @property
    def item(self) -> entity.Entity:
        return self.entity

    def number(self, of):
        with self.area.make(carryable.Containing) as contain:
            if isinstance(of, str):
                return contain.number_of_named(of)
            return contain.number_of_kind(of)

    def kind(self, name: str) -> kinds.Kind:
        return self.entity.get_kind(name)

    def visible(self):
        with self.entity.make(mechanics.Visibility) as vis:
            vis.make_visible()

    def invisible(self):
        with self.entity.make(mechanics.Visibility) as vis:
            vis.make_invisible()

    def is_invisible(self):
        return self.entity.make(mechanics.Visibility).is_invisible

    def go(self, area) -> Sequence[game.Action]:
        return [actions.Go(area=area)]

    def make_hands(self, table) -> Sequence[game.Action]:
        item = self.make_item_from_table(table, creator=self.entity)
        return [creation.Make(item=finders.StaticItem(item=item))]

    def make_here(self, table):
        item = self.make_item_from_table(table, creator=self.ctx.creator)
        return [actions.AddItemArea(area=self.area, item=item)]
