import sys
import json
import asyncclick as click

from loggers import get_logger

log = get_logger("dimsum.cli")


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
