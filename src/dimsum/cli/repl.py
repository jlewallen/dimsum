import asyncclick as click
import logging
import sys

import config

import cli.interactive as interactive

log = logging.getLogger("dimsum.cli")


@click.group()
def commands():
    pass


@commands.command()
@click.option(
    "--path",
    required=True,
    help="Database to open in a repl.",
    type=click.Path(),
)
@click.option(
    "--username",
    default="jlewallen",
    help="Username, used as key for player.",
)
async def repl(path: str, username: str):
    """Allow easy one-person interaction with a world."""
    cfg = config.symmetrical(path)
    repl = Repl(cfg, username)
    while True:
        safe = await repl.iteration()
        if not safe:
            break


class Repl:
    def __init__(self, cfg: config.Configuration, name: str):
        super().__init__()
        self.cfg = cfg
        self.domain = cfg.make_domain()
        self.loop = interactive.Interactive(self.domain, name)

    async def read_command(self):
        return sys.stdin.readline().strip()

    async def iteration(self):
        command = await self.read_command()

        if command is None:
            return False

        if command == "":
            return True

        try:
            await self.loop.handle(command)
        except:
            log.exception("error", exc_info=True)

        return True

    def write(self, s: str, end=None):
        sys.stdout.write(s)
