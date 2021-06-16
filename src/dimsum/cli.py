#!env/bin/python3

import sys
import logging
import asyncio
import jinja2
import json
import argparse
import os

import luaproxy
import handlers
import world
import messages
import persistence
import entity


def get_color(e: entity.Entity) -> str:
    map = {
        "World": "white",
        "Animal": "darkseagreen",
        "Player": "coral",
        "Item": "khaki",
        "Exit": "salmon",
        "Area": "skyblue",
        "Recipe": "thistle",
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
        bus = messages.TextBus(handlers=[handlers.WhateverHandlers])
        the_world = world.World(bus, luaproxy.context_factory)
        db = persistence.SqliteDatabase()
        await db.open(path)
        await db.load(the_world)

        if args.graph:
            name = os.path.splitext(path)[0]
            await db.write("{0}.json".format(name))
            await graph("{0}.dot".format(name), the_world)

        if args.repl:
            pass


if __name__ == "__main__":
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    asyncio.run(main())
