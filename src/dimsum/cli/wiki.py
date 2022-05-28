import asyncio
import asyncclick as click
import os.path
import glob
from typing import List, Optional

import config
import domains
from loggers import get_logger
from plugins.helping import WriteHelp

import cli.interactive as interactive

log = get_logger("dimsum.cli")


@click.group()
def commands():
    pass


@commands.command()
@click.option(
    "--directory",
    multiple=True,
    required=True,
    help="Markdown paths",
)
@click.option(
    "--database",
    help="Database file",
    type=click.Path(),
)
@click.option(
    "--user",
    required=True,
    help="Username",
    type=click.Path(),
)
async def load_wiki(
    directory: List[str],
    database: str,
    user: str,
):
    """Load markdown files into help system."""

    cfg = config.symmetrical(database or ":memory:")
    domain = cfg.make_domain()

    initializing = interactive.InitializeWorld(domain)
    player_keys = await initializing.initialize([user])

    with domain.session() as session:
        world = await session.prepare()
        player = await session.materialize(key=player_keys[0])

        for dir_path in directory:
            for file in glob.glob(os.path.join(dir_path, "*.md")):
                name, _ = os.path.splitext(os.path.basename(file))
                log.info("name=%s", name)
                with open(file, "r") as reading:
                    body = reading.read()
                    if name == "WelcomePage":
                        await session.perform(WriteHelp(None, body), person=player)
                    else:
                        await session.perform(WriteHelp(name, body), person=player)

        await session.save()

    await domain.close()
