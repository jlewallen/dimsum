#!env/bin/python3

import sys
import logging
import asyncio
import jinja2
import json
import argparse
import os

import model.sugar as sugar
import model.properties as properties
import model.world as world
import model.entity as entity
import model.library as library
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

log = logging.getLogger("dimsum-repl")


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

        player = scopes.alive(
            key=self.name,
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


def get_color(e: entity.Entity) -> str:
    map = {
        "World": "white",
        "Animal": "darkseagreen",
        "Player": "coral",
        "Item": "khaki",
        "Exit": "salmon",
        "Area": "skyblue",
        "Recipe": "thistle",
        "Chimera": "lavenderblush",
        "Entity": "lavenderblush",
    }
    return map[e.klass]


async def graph(fn: str, world: world.World):
    template_loader = jinja2.FileSystemLoader(searchpath="./")
    template_env = jinja2.Environment(loader=template_loader)
    template = template_env.get_template("graph.template")
    with open(fn, "w") as file:
        file.write(template.render(world=world, get_color=get_color))
        file.write("\n\n")


async def main():
    parser = argparse.ArgumentParser(description="dimsum cli")
    parser.add_argument("-r", "--repl", default=False, action="store_true")
    parser.add_argument("-g", "--graph", default=False, action="store_true")
    parser.add_argument("databases", nargs="*")
    args = parser.parse_args()

    for path in args.databases:
        if args.graph:
            bus = messages.TextBus(handlers=[handlers.WhateverHandlers])
            the_world = world.World(bus, luaproxy.context_factory)
            db = persistence.SqliteDatabase()
            await db.open(path)
            await db.load(the_world)

            name = os.path.splitext(path)[0]
            await db.write("{0}.json".format(name))
            await graph("{0}.dot".format(name), the_world)

        if args.repl:
            repl = Repl(path, "jlewallen")
            while True:
                safe = await repl.iteration()
                if not safe:
                    break


if __name__ == "__main__":
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    asyncio.run(main())
