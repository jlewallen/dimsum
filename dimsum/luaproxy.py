from typing import Sequence

import logging
import lupa

import entity
import game
import world
import actions
import props

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
        if isinstance(thing, game.Person):
            return LupaPerson(self, thing)
        if isinstance(thing, game.Animal):
            return LupaAnimal(self, thing)
        if isinstance(thing, game.Area):
            return LupaArea(self, thing)
        if isinstance(thing, game.Item):
            return LupaItem(self, thing)
        if isinstance(thing, entity.Entity):
            raise Exception(
                "no wrapper for entity: %s (%s)"
                % (
                    thing,
                    type(thing),
                )
            )
        return thing


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
        self.entity.details.map[key] = self.unlua(value)

    def __getitem__(self, key: str):
        log.info("entity:entity g: %s %s" % (str(self), str(key)))
        if key in self.entity.details.map:
            return self.entity.details.map[key]
        if hasattr(self, key):
            return getattr(self, key)
        if hasattr(self.entity, key):
            return getattr(self.entity, key)
        return None

    def make_item_from_table(self, table, **kwargs) -> game.Item:
        log.info(
            "area:make: %s",
            ", ".join(["%s=%s" % (key, value) for key, value in table.items()]),
        )

        kind = table["kind"] if "kind" in table else entity.Kind()
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
    def world(self) -> world.World:
        assert isinstance(self.entity, world.World)
        return self.entity


class LupaArea(LupaEntity):
    @property
    def area(self) -> game.Area:
        assert isinstance(self.entity, game.Area)
        return self.entity

    def number(self, of):
        if isinstance(of, str):
            return self.area.number_of_named(of)
        return self.area.number_of_kind(of)

    def make(self, table):
        item = self.make_item_from_table(table, creator=self.ctx.creator)
        return [actions.AddItemArea(area=self.area, item=item)]


class LupaItem(LupaEntity):
    @property
    def item(self) -> game.Item:
        assert isinstance(self.entity, game.Item)
        return self.entity

    def kind(self, name: str) -> entity.Kind:
        return self.entity.get_kind(name)


class LupaLivingCreature(LupaEntity):
    def visible(self):
        return self.entity.make_visible()

    def invisible(self):
        return self.entity.make_invisible()

    def is_invisible(self):
        return self.entity.is_invisible

    def go(self, area) -> Sequence[game.Action]:
        return [actions.Go(area=area)]

    def make(self, table) -> Sequence[game.Action]:
        item = self.make_item_from_table(table, creator=self.entity)
        return [actions.Make(item=item)]


class LupaPerson(LupaLivingCreature):
    @property
    def person(self) -> game.Person:
        assert isinstance(self.entity, game.Person)
        return self.entity


class LupaAnimal(LupaLivingCreature):
    @property
    def animal(self) -> game.Animal:
        assert isinstance(self.entity, game.Animal)
        return self.entity
