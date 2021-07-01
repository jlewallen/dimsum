#!env/bin/python3

import sys
import logging
import logging.config
import asyncio
import asyncclick as click
import json
import os

import cli.repl
import cli.graph
import cli.export
import cli.query
import cli.server
import cli.broker
import cli.dummy

log = logging.getLogger("dimsum.cli")


def configure_logging():
    with open("logging.json", "r") as file:
        config = json.loads(file.read())  # TODO Parsing logging config JSON
        logging.config.dictConfig(config)


@click.group()
@click.option("--debug/--no-debug", default=False)
def command_line(debug: bool):
    configure_logging()


if __name__ == "__main__":
    sources = [
        cli.repl.commands,
        cli.graph.commands,
        cli.export.commands,
        cli.query.commands,
        cli.server.commands,
        cli.broker.commands,
        cli.dummy.commands,
    ]
    for g in sources:
        for n, c in g.commands.items():
            command_line.add_command(c)
    command_line()  # type: ignore
