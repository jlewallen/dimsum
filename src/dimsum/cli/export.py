from typing import Optional
import sys, os
import asyncclick as click

from loggers import get_logger
import cli.utils as utils

log = get_logger("dimsum.cli")


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
@click.option(
    "--gid",
    required=False,
    help="Specific entity to export.",
)
@click.option(
    "--key",
    required=False,
    help="Specific entity to export.",
)
async def export(path: str, gid: Optional[int], key: Optional[str]):
    """Exporting entities from a database."""
    domain = await utils.open_domain(path)

    await domain.store.write(sys.stdout, gid=gid, key=key)  # type:ignore

    await domain.close()
