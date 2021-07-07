#!env/bin/python3

import json
import logging
import logging.config

import asyncclick as click
import cli.broker
import cli.dummy
import cli.export
import cli.graph
import cli.query
import cli.repl
import cli.server

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
