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

log = logging.getLogger("dimsum-cli")


@click.group()
def commands():
    pass


@commands.command()
async def query():
    """Execute a standard query."""
    log.info("%s", json.loads(sys.stdin.read()))
