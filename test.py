import asyncio
import logging
import sys
import lark

import game
import props
import actions
import grammar
import evaluator
import luaproxy


class TestWorld:
    def __init__(self):
        self.bus = game.EventBus()
        self.world = game.World(self.bus, luaproxy.context_factory)
        self.jacob = game.Player(
            creator=self.world,
            details=props.Details("Jacob", desc="Curly haired bastard."),
        )
        self.player = self.jacob
        self.area = game.Area(creator=self.player, details=props.Details("Living room"))
        self.world.register(self.area)
        self.l = grammar.create_parser()

    def add_simple_area_here(self, door, name):
        door = game.Item(creator=self.player, details=props.Details(door))
        area = game.Area(creator=self.player, details=props.Details(name))
        door.link_area(area)
        self.area.add_item(door)
        self.world.register(door)
        self.world.register(area)
        return area

    async def add_carla(self):
        self.carla = game.Player(
            creator=self.world,
            details=props.Details("Carla", desc="Chief Salad Officer."),
        )
        return await self.world.perform(self.carla, actions.Join())

    async def add_tomi(self):
        self.tomi = game.Player(
            creator=self.world,
            details=props.Details("Tomi", desc="Chief Crying Officer."),
        )
        return await self.world.perform(self.tomi, actions.Join())

    async def initialize(self):
        self.world.add_area(self.area)
        await self.world.perform(self.jacob, actions.Join())

    def get_default_area(self):
        return self.area

    def add_item(self, item):
        self.world.register(item)
        self.get_default_area().add_item(item)
        return item

    async def execute(self, command: str):
        logging.info("executing: %s" % (command,))
        tree = self.l.parse(command)
        logging.info("parsed: %s" % (tree,))
        action = evaluator.create(self.world, self.player).transform(tree)
        response = await self.world.perform(self.player, action)
        logging.info("response: %s" % (response,))
        return response
