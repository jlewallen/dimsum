import sys
import os
import json
import asyncclick as click

from loggers import get_logger
from model import CompiledJson
import cli.utils as utils

log = get_logger("dimsum.cli")


@click.group()
def commands():
    pass


@commands.command("import")
@click.option(
    "--path",
    required=True,
    help="Database to import into.",
    type=click.Path(exists=True),
)
async def load(path: str):
    """Importing entities back into a database."""
    domain = await utils.open_domain(path)
    incoming = json.loads(sys.stdin.read())
    compiled = {
        entity["key"]: CompiledJson(json.dumps(entity), entity) for entity in incoming
    }
    log.info("updating storage %d entities", len(incoming))
    await domain.store.update(compiled)
