#!env/bin/python3

import sys
import logging
import asyncio
import asyncclick as click
import os

log = logging.getLogger("dimsum-cli")

import cli.repl
import cli.graph
import cli.export
import cli.query
import cli.server


@click.group()
@click.option("--debug/--no-debug", default=False)
def command_line(debug: bool):
    if debug:
        logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
    else:
        logging.basicConfig(stream=sys.stderr, level=logging.INFO)


if __name__ == "__main__":
    sources = [
        cli.repl.commands,
        cli.graph.commands,
        cli.export.commands,
        cli.query.commands,
        cli.server.commands,
    ]
    for g in sources:
        for n, c in g.commands.items():
            command_line.add_command(c)
    command_line()  # type: ignore
