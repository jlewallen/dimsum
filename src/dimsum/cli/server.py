import logging
import asyncclick as click
import os
import sys

import quart
import quart_cors

from hypercorn.config import Config
from hypercorn.asyncio import serve

import asyncio

import web

import model.world as world
import model.entity as entity
import model.scopes as scopes

import cli.utils as utils

log = logging.getLogger("dimsum-cli")


@click.group()
def commands():
    pass


@commands.command()
@click.option(
    "--path",
    required=True,
    help="Database to export from.",
    type=click.Path(exists=True),
)
async def server(path: str):
    """Serve a database."""
    # domain = await utils.open_domain(path)

    config = Config()
    config.bind = ["0.0.0.0:5000"]
    await serve(web.create(None), config)
