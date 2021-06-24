import asyncclick as click
import base64
import logging
import sys

import model.sugar as sugar
import model.properties as properties
import model.world as world
import model.domains as domains
import model.scopes as scopes
import model.library as library

import default.actions as actions
import default
import digging
import simple
import fallback

import grammars

import luaproxy
import handlers
import messages
import storage

log = logging.getLogger("dimsum-cli")


@click.group()
def commands():
    pass


@commands.command()
@click.option(
    "--path",
    required=True,
    help="Database to open in a repl.",
    type=click.Path(),
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
        self.domain = domains.Domain(store=storage.SqliteStorage(fn), empty=True)
        self.world = None

    async def get_player(self):
        if self.world is None:
            self.world = self.domain.world
            assert self.world

        if self.domain.registrar.empty():
            log.info("creating example world")
            generics, area = library.create_example_world(self.world)
            self.domain.registrar.add_entities(generics.all)
            self.domain.add_area(area)
            await self.domain.save()

        key = base64.b64encode(self.name.encode("utf-8")).decode("utf-8")
        if self.domain.registrar.contains(key):
            player = self.domain.registrar.find_by_key(key)
            return player

        player = scopes.alive(
            key=key,
            creator=self.world,
            props=properties.Common(self.name, desc="A repl user"),
        )
        await self.domain.perform(actions.Join(), player)
        await self.save()
        return player

    async def save(self):
        await self.domain.save()

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

        reply = await self.domain.perform(action, player)
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
