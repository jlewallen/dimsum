#!env/bin/python3

import logging
import asyncio
import time
import sys
import os

import web
import bot
import sshd

import ariadne.asgi
import ariadne

import schema as schema_factory
import config

from hypercorn.config import Config
from hypercorn.asyncio import serve

if __name__ == "__main__":
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)

    shutdown_event = asyncio.Event()

    gb = bot.GameBot(os.getenv("DISCORD_TOKEN"))
    web_app = web.create(gb)

    schema = schema_factory.create()
    gql_app = ariadne.asgi.GraphQL(schema, debug=True)

    if False:
        gb.bot.loop.create_task(
            web_app.run_task("0.0.0.0", 5000, shutdown_trigger=shutdown_event.wait)
        )
        gb.bot.loop.create_task(sshd.start_server(gb))
        gb.run()
    else:
        asyncio.run(serve(gql_app, Config()))  # type:ignore
else:
    cfg = config.get(None)
    schema = schema_factory.create()
    app = ariadne.asgi.GraphQL(schema, context_value=schema_factory.context, debug=True)
