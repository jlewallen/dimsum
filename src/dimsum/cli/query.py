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
import config as configuration
import serializing

import schema as schema_factory
from schema import AriadneContext

log = logging.getLogger("dimsum-cli")


@click.group()
def commands():
    pass


@commands.command()
@click.option(
    "--config",
    help="Path to configuration file.",
    type=click.Path(exists=True),
)
@click.option(
    "--database",
    help="Path to database file.",
    type=click.Path(exists=True),
)
async def query(config: str, database: str):
    """Execute a standard query."""

    def get_config():
        if config:
            return configuration.get(config)
        return configuration.Configuration(database=database, session_key="session-key")

    body = None
    try:
        unparsed_body = sys.stdin.read()
        body = json.loads(unparsed_body)
    except:
        sys.stdout.write(json.dumps(make_error("parsing")))
        return

    cfg = get_config()
    domain = domains.Domain(empty=True, store=cfg.make_store())
    context = AriadneContext(domain, cfg)
    schema = schema_factory.create()
    ok, actual = await ariadne.graphql(schema, data=body, context_value=context)

    sys.stdout.write(serializing.serialize(actual, indent=True))


def make_error(message: str):
    return {"errors": [{"message": message}]}
