#!env/bin/python3

import logging
import asyncio
import time
import sys
import os

import web
import bot


if __name__ == "__main__":
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)

    shutdown_event = asyncio.Event()
    gb = bot.GameBot(os.getenv("DISCORD_TOKEN"))
    gb.bot.loop.create_task(
        web.app.run_task("0.0.0.0", 5000, shutdown_trigger=shutdown_event.wait)
    )
    gb.run()
