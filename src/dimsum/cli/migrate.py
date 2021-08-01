import sys
import os
import json
import asyncclick as click

from loggers import get_logger
from model import CompiledJson
import cli.utils as utils
import migration

log = get_logger("dimsum.cli")


@click.group()
def commands():
    pass


@commands.command()
@click.option(
    "--path",
    required=True,
    help="Database to migrate.",
    type=click.Path(exists=True),
)
async def migrate(path: str):
    """
    Migrating a database.
    """
    domain = await utils.open_domain(path)
    with domain.session() as session:
        m = migration.Migrator(domain)
        await m.migrate(session)
        await session.save()
