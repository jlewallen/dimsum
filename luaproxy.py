from typing import Sequence

import logging
import lupa

import entity
import game
import actions
import props

log = logging.getLogger("dimsum")


class LupaEntity:
    def __init__(self, entity: entity.Entity):
        self.entity = entity

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
        self.entity.details.map[key] = self.unlua(value)

    def __getitem__(self, key: str):
        log.info("entity:entity g: %s %s" % (str(self), str(key)))
        if key in self.entity.details.map:
            return self.entity.details.map[key]
        if hasattr(self, key):
            return getattr(self, key)
        return None

    def make_item_from_table(self, table, **kwargs) -> game.Item:
        log.info(
            "area:make: %s",
            ", ".join(["%s=%s" % (key, value) for key, value in table.items()]),
        )

        kind = table["kind"] if "kind" in table else game.Kind()
        del table["kind"]

        quantity = table["quantity"] if "quantity" in table else 1
        del table["quantity"]

        details = props.Details(name=table.name)
        del table["name"]

        for key, value in table.items():
            details.map[key] = value

        item = game.Item(details=details, quantity=quantity, kind=kind, **kwargs)

        return item


class LupaWorld(LupaEntity):
    @property
    def world(self) -> game.World:
        if not isinstance(self.entity, game.World):
            raise Exception()
        return self.entity


class LupaArea(LupaEntity):
    @property
    def area(self) -> game.Area:
        if not isinstance(self.entity, game.Area):
            raise Exception()
        return self.entity

    def make(self, table):
        item = self.make_item_from_table(table, owner=self.area)
        return [actions.AddItemArea(area=self.area, item=item)]


class LupaItem(LupaEntity):
    @property
    def item(self) -> game.Item:
        if not isinstance(self.entity, game.Item):
            raise Exception()
        return self.entity

    def kind(self, name: str) -> game.Kind:
        key = "k:" + name
        if not key in self.entity.details.map:
            self.entity.details.map[key] = game.Kind()
        return self.entity.details.map[key]


class LupaPerson(LupaEntity):
    @property
    def person(self) -> game.Person:
        if not isinstance(self.entity, game.Person):
            raise Exception()
        return self.entity

    def visible(self):
        return self.entity.make_visible()

    def invisible(self):
        return self.entity.make_invisible()

    def is_invisible(self):
        return self.entity.is_invisible

    def go(self, area) -> Sequence[game.Action]:
        return [actions.Go(area=area)]

    def make(self, table) -> Sequence[game.Action]:
        item = self.make_item_from_table(table, owner=self.person)
        return [actions.Make(item=item)]


def wrap(thing):
    if thing is None:
        return None
    if isinstance(thing, list):
        return [wrap(e) for e in thing]
    if isinstance(thing, dict):
        return {key: wrap(value) for key, value in thing.items()}
    if isinstance(thing, game.World):
        return LupaWorld(thing)
    if isinstance(thing, game.Person):
        return LupaPerson(thing)
    if isinstance(thing, game.Area):
        return LupaArea(thing)
    if isinstance(thing, game.Item):
        return LupaItem(thing)
    if isinstance(thing, entity.Entity):
        raise Exception(
            "no wrapper for entity: %s (%s)"
            % (
                thing,
                type(thing),
            )
        )
    return thing
