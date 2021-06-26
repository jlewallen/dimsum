import logging
import asyncclick as click
import os
import sys
import jsonpickle
import json

import model.world as world
import model.entity as entity
import model.scopes as scopes

import cli.utils as utils

log = logging.getLogger("dimsum.cli")


@click.group()
def commands():
    pass


@commands.command()
@click.option("--ok/--no-ok", default=False, help="Reply is ok.")
async def dummy(ok: bool):
    """
    Return dummy replies for testing.
    """
    sys.stdout.write(json.dumps({"ok": ok}))
