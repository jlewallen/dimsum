import logging
import asyncclick as click
import os
import sys

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
async def export(path: str):
    """Exporting entities from a database."""
    world, db = await utils.open_world(path)
    name = os.path.splitext(path)[0]
    await db.write(sys.stdout)
