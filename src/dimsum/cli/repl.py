import asyncclick as click
import base64
import logging
import sys

import model.sugar as sugar
import model.properties as properties
import model.world as world
import model.scopes as scopes

import default.actions as actions
import default
import digging
import simple
import fallback

import grammars

import luaproxy
import handlers
import messages
import persistence


log = logging.getLogger("dimsum-cli")


@click.group()
def commands():
    pass


@commands.command()
@click.option(
    "--path",
    required=True,
    help="Database to open in a repl.",
    type=click.Path(exists=True),
)
async def repl(path: str):
    """Allow easy one-person interaction with a world."""
    repl = Repl(path, "jlewallen")
    while True:
        safe = await repl.iteration()
        if not safe:
            break


class Repl:
    def __init__(self, fn: str, name: str):
        super().__init__()
        self.l = grammars.create_parser()
        self.fn = fn
        self.name = name
        self.world = None
        self.bus = messages.TextBus(handlers=[handlers.WhateverHandlers])
        self.db = persistence.SqliteDatabase()

    async def get_player(self):
        if self.world is None:
            self.world = world.World(self.bus, luaproxy.context_factory)
            await self.db.open(self.fn)
            await self.db.load(self.world)

        if self.world.empty():
            log.info("creating example world")
            generics, area = library.create_example_world(self.world)
            self.world.add_entities(generics.all)
            self.world.add_area(area)
            await self.db.save(self.world)

        if self.world.contains(self.name):
            player = self.world.find_by_key(self.name)
            return player

        key = base64.b64encode(self.name.encode("utf-8")).decode("utf-8")
        player = scopes.alive(
            key=key,
            creator=self.world,
            props=properties.Common(self.name, desc="A repl user"),
        )
        await self.world.perform(actions.Join(), player)
        await self.save()
        return player

    async def save(self):
        db = persistence.SqliteDatabase()
        await db.open(self.fn)
        await db.save(self.world)

    async def read_command(self):
        return sys.stdin.readline().strip()

    async def iteration(self):
        player = await self.get_player()

        command = await self.read_command()

        if command is None:
            return False

        if command == "":
            return True

        tree, create_evaluator = self.l.parse(command.strip())
        tree_eval = create_evaluator(self.world, player)
        log.info(str(tree))
        action = tree_eval.transform(tree)

        reply = await self.world.perform(action, player)
        await self.save()

        visitor = messages.ReplyVisitor()
        visual = reply.accept(visitor)
        log.info(
            "%s" % (visual),
        )

        self.write("\n", end="")

        if "title" in visual:
            self.write(visual["title"], end="")
            self.write("\n", end="")

        if "text" in visual:
            self.write(visual["text"], end="")
            self.write("\n", end="")

        if "description" in visual:
            self.write("\n", end="")
            self.write(visual["description"], end="")

        self.write("\n", end="")

        return True

    def write(self, s: str, end=None):
        sys.stdout.write(s)
