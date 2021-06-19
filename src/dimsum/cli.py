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


if __name__ == "__main__":
    logging.basicConfig(stream=sys.stderr, level=logging.INFO)

    cli = click.CommandCollection(  # type: ignore
        sources=[
            cli.repl.commands,
            cli.graph.commands,
            cli.export.commands,
            cli.query.commands,
        ]
    )
    cli()  # type: ignore
