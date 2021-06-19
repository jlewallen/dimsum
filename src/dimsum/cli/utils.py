from typing import Tuple

import model.world as world

import luaproxy
import handlers
import messages
import persistence


async def open_world(path: str) -> Tuple[world.World, persistence.SqliteDatabase]:
    bus = messages.TextBus(handlers=[handlers.WhateverHandlers])
    w = world.World(bus, luaproxy.context_factory)
    db = persistence.SqliteDatabase()
    await db.open(path)
    await db.load(w)
    return w, db
