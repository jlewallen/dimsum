import logging
import asyncclick as click
import os
import sys
import jsonpickle
import json

import model.world as world
import model.entity as entity
import model.scopes as scopes
import model.domains as domains

import cli.utils as utils

import ariadne

import schema as schema_factory
from schema import AriadneContext

log = logging.getLogger("dimsum-cli")


@click.group()
def commands():
    pass


@commands.command()
async def query():
    """Execute a standard query."""

    body = None
    try:
        unparsed_body = sys.stdin.read()
        body = json.loads(unparsed_body)
    except:
        sys.stdout.write(json.dumps(make_error("parsing")))
        return

    schema = schema_factory.create()
    domain = domains.Domain()
    ok, actual = await ariadne.graphql(
        schema,
        data=body,
        context_value=AriadneContext(domain),
    )

    sys.stdout.write(json.dumps(actual))


def make_error(message: str):
    return {"errors": [{"message": message}]}
