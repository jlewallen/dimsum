#!env/bin/python3

import json, warnings
import logging.config
import asyncclick as click
from rich.logging import RichHandler
from rich.console import Console

from loggers import get_logger

warnings.filterwarnings(
    action="ignore",
    category=UserWarning,
    message="Blowfish has been deprecated",
)
warnings.filterwarnings(
    action="ignore",
    category=UserWarning,
    message="CAST5 has been deprecated",
)
warnings.filterwarnings(
    action="ignore",
    category=UserWarning,
    message="SEED has been deprecated",
)

import cli.broker
import cli.dummy
import cli.export
import cli.importing
import cli.migrate
import cli.graph
import cli.query
import cli.repl
import cli.server
import cli.wiki
import cli.diff

log = get_logger("dimsum.cli")


def configure_logging(colors: bool):
    with open("logging.json", "r") as file:
        config = json.loads(file.read())  # TODO Parsing logging config JSON
        if colors and "handlers" in config:
            handlers = config["handlers"]
            if "console" in handlers:
                handlers["stderr"] = handlers["console"]
                handlers["console"] = {
                    "class": "rich.logging.RichHandler",
                    "console": Console(stderr=True),
                }
        logging.config.dictConfig(config)


@click.group()
@click.option("--debug/--no-debug", default=False)
@click.option("--colors/--no-colors", default=True)
def command_line(debug: bool, colors: bool):
    configure_logging(colors)


if __name__ == "__main__":
    sources = [
        cli.repl.commands,
        cli.graph.commands,
        cli.export.commands,
        cli.importing.commands,
        cli.migrate.commands,
        cli.query.commands,
        cli.server.commands,
        cli.broker.commands,
        cli.wiki.commands,
        cli.diff.commands,
        cli.dummy.commands,
    ]
    for g in sources:
        for n, c in g.commands.items():
            command_line.add_command(c)
    command_line()
