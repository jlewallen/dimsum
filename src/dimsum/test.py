from typing import List

import asyncio
import logging
import sys
import lark

import properties
import grammar
import game
import world
import envo
import things
import animals
import actions
import luaproxy
import bus
import messages
import handlers
import reply
import serializing
import persistence
import movement

import sugar
import digging
import simple

log = logging.getLogger("dimsum")


def create_empty_world():
    return world.World(bus.EventBus(), luaproxy.context_factory)


class TestWorld:
    def __init__(self):
        self.bus = messages.TextBus(handlers=[handlers.WhateverHandlers])
        self.world = world.World(self.bus, luaproxy.context_factory)
        self.jacob = animals.Player(
            creator=self.world,
            props=properties.Common("Jacob", desc="Curly haired bastard."),
        )
        self.player = self.jacob
        self.l = grammar.create_parser()

    def add_simple_area_here(self, door, name):
        door = things.Item(creator=self.player, props=properties.Common(door))
        area = envo.Area(creator=self.player, props=properties.Common(name))
        with door.make(movement.MovementMixin) as nav:
            nav.link_area(area)
        self.area.add_item(door)
        self.world.register(door)
        self.world.register(area)
        return area

    async def add_carla(self):
        self.carla = animals.Player(
            creator=self.world,
            props=properties.Common("Carla", desc="Chief Salad Officer."),
        )
        return await self.world.perform(actions.Join(), self.carla)

    async def add_tomi(self):
        self.tomi = animals.Player(
            creator=self.world,
            props=properties.Common("Tomi", desc="Chief Crying Officer."),
        )
        return await self.world.perform(actions.Join(), self.tomi)

    async def initialize(self, area=None, **kwargs):
        self.area = area
        if not self.area:
            self.area = envo.Area(
                creator=self.player, props=properties.Common("Living room")
            )
            self.world.register(self.area)
        self.world.add_area(self.area)
        await self.world.perform(actions.Join(), self.jacob)

    def get_default_area(self):
        return self.area

    def add_item(self, item):
        self.world.register(item)
        self.get_default_area().add_item(item)
        return item

    def dumps(self, item) -> str:
        return serializing.serialize(item, indent=4)

    async def execute(self, command: str, person=None, **kwargs):
        if not person:
            person = self.player
        log.info("executing: %s" % (command,))
        tree, create_evaluator = self.l.parse(command)
        log.info("parsed: %s" % (tree,))
        tree_eval = create_evaluator(self.world, person)
        action = tree_eval.transform(tree)
        assert action
        assert isinstance(action, game.Action)
        response = await self.world.perform(action, person)
        log.info("response: %s" % (response,))
        return response

    async def success(self, *commands: str, **kwargs):
        for command in commands:
            r = await self.execute(command, **kwargs)
            if not isinstance(r, game.Failure):
                return r
            log.error("reply: %s", r)
            assert not isinstance(r, game.Failure)

    async def failure(self, command: str, **kwargs):
        r = await self.execute(command, **kwargs)
        assert isinstance(r, game.Failure)
        return r

    async def realize(self):
        pass

    async def save(self, fn: str):
        db = persistence.SqliteDatabase()
        await db.open(fn)
        await db.purge()
        await db.save(self.world)
