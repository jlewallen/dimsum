from typing import TextIO

import logging
import asyncclick as click
import os
import sys
import asyncio
import ipaddress

import proxy

import ariadne.asgi
import ariadne
import uvicorn

import config
import sshd
import routing
import schema as schema_factory

import model.domains as domains

log = logging.getLogger("dimsum-cli")


@click.group()
def commands():
    pass


class SecureSession(sshd.CommandHandler):
    def __init__(self, username: str = None):
        super().__init__()
        self.username = username

    async def handle(self, username: str, line: str, back: TextIO):
        log.info("handle: %s '%s'", username, line)
        back.write("hey here!\n")


@commands.command()
@click.option(
    "--path",
    required=True,
    help="Database to serve from.",
    type=click.Path(exists=True),
)
async def server(path: str):
    """
    Serve a database.
    """
    session_key = "random"
    cfg = config.Configuration(database=path, session_key=session_key)
    schema = schema_factory.create()
    app = ariadne.asgi.GraphQL(
        schema, context_value=schema_factory.context(cfg), debug=True
    )

    def create_ssh_session(username: str = None):
        return SecureSession(username)

    if False:
        with proxy.start(
            ["--enable-web-server"],
            hostname=ipaddress.IPv4Address("0.0.0.0"),
            port=8899,
            plugins=[proxy.plugin.ReverseProxyPlugin],
        ):
            pass

    loop = asyncio.get_event_loop()
    gql_config = uvicorn.Config(app=app, loop=loop)
    gql_server = uvicorn.Server(gql_config)
    gql_task = loop.create_task(gql_server.serve())
    sshd_task = loop.create_task(sshd.start_server(create_ssh_session))
    await asyncio.gather(sshd_task, gql_task)

    log.info("done")
