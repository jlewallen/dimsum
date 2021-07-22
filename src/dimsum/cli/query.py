import sys
import json
import ariadne
import asyncclick as click

import serializing
import config as configuration
import schema as schema_factory
from loggers import get_logger
from schema import AriadneContext

log = get_logger("dimsum.cli")


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
        return configuration.symmetrical(database)

    body = None
    try:
        unparsed_body = sys.stdin.read()
        body = json.loads(unparsed_body)  # TODO Parsing gql JSON
    except:
        sys.stdout.write(json.dumps(make_error("parsing")))
        return

    cfg = get_config()
    domain = cfg.make_domain()
    context = AriadneContext(
        cfg,
        domain,
        None,  # type:ignore
    )
    schema = schema_factory.create()
    ok, actual = await ariadne.graphql(schema, data=body, context_value=context)

    s = serializing.serialize(actual, indent=True)
    if s:
        sys.stdout.write(s)


def make_error(message: str):
    return {"errors": [{"message": message}]}
