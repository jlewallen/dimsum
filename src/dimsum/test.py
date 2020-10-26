from typing import List

import asyncio
import logging
import sys
import lark

import props
import grammar
import game
import world
import envo
import things
import animals
import actions
import evaluator
import luaproxy
import bus
import messages
import handlers
import reply

log = logging.getLogger("dimsum")


def create_empty_world():
    return world.World(bus.EventBus(), luaproxy.context_factory)


class TestWorld:
    def __init__(self):
        self.bus = messages.TextBus(handlers=[handlers.WhateverHandlers])
        self.world = world.World(self.bus, luaproxy.context_factory)
        self.jacob = animals.Player(
            creator=self.world,
            details=props.Details("Jacob", desc="Curly haired bastard."),
        )
        self.player = self.jacob
        self.area = envo.Area(creator=self.player, details=props.Details("Living room"))
        self.world.register(self.area)
        self.l = grammar.create_parser()

    def add_simple_area_here(self, door, name):
        door = things.Item(creator=self.player, details=props.Details(door))
        area = envo.Area(creator=self.player, details=props.Details(name))
        door.link_area(area)
        self.area.add_item(door)
        self.world.register(door)
        self.world.register(area)
        return area

    async def add_carla(self):
        self.carla = animals.Player(
            creator=self.world,
            details=props.Details("Carla", desc="Chief Salad Officer."),
        )
        return await self.world.perform(actions.Join(), self.carla)

    async def add_tomi(self):
        self.tomi = animals.Player(
            creator=self.world,
            details=props.Details("Tomi", desc="Chief Crying Officer."),
        )
        return await self.world.perform(actions.Join(), self.tomi)

    async def initialize(self):
        self.world.add_area(self.area)
        await self.world.perform(actions.Join(), self.jacob)

    def get_default_area(self):
        return self.area

    def add_item(self, item):
        self.world.register(item)
        self.get_default_area().add_item(item)
        return item

    async def execute(self, command: str):
        log.info("executing: %s" % (command,))
        tree = self.l.parse(command)
        log.info("parsed: %s" % (tree,))
        action = evaluator.create(self.world, self.player).transform(tree)
        assert action
        assert isinstance(action, game.Action)
        response = await self.world.perform(action, self.player)
        log.info("response: %s" % (response,))
        return response

    async def success(self, *commands: str):
        for command in commands:
            r = await self.execute(command)
            if not isinstance(r, reply.Failure):
                return r
            log.error("reply: %s", r)
            assert not isinstance(r, reply.Failure)

    async def failure(self, command: str):
        r = await self.execute(command)
        assert isinstance(r, reply.Failure)
        return r

    async def realize(self):
        pass
