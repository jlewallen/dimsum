#!env/bin/python3

import logging
import asyncio
import time
import sys
import os

import web
import bot
import sshd

if __name__ == "__main__":
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)

    shutdown_event = asyncio.Event()

    gb = bot.GameBot(os.getenv("DISCORD_TOKEN"))
    webApp = web.create(gb)
    gb.bot.loop.create_task(
        webApp.run_task("0.0.0.0", 5000, shutdown_trigger=shutdown_event.wait)
    )
    gb.bot.loop.create_task(sshd.start_server(gb))
    gb.run()
