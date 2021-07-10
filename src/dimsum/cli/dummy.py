import sys
import json
import logging
import asyncclick as click

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
