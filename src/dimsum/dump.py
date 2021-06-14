#!/usr/bin/python3

import sys
import logging
import asyncio
import jinja2
import json

import luaproxy
import handlers
import world
import messages
import persistence
import entity


def get_color(e: entity.Entity) -> str:
    map = {
        "Animal": "darkseagreen",
        "Player": "coral",
        "Item": "khaki",
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
    bus = messages.TextBus(handlers=[handlers.WhateverHandlers])
    the_world = world.World(bus, luaproxy.context_factory)
    db = persistence.SqliteDatabase()
    await db.open("world.sqlite3")
    await db.load(the_world)
    await db.write("world.json")
    await graph("world.dot", the_world)


if __name__ == "__main__":
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    asyncio.run(main())
