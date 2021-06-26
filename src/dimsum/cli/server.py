from typing import TextIO

import logging
import asyncclick as click
import asyncio
import ipaddress

import proxy

import ariadne.asgi
import uvicorn

import config
import schema as schema_factory
import sshd

import cli.interactive as interactive

log = logging.getLogger("dimsum.cli")


@click.group()
def commands():
    pass


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
        return interactive.Interactive(cfg, username)

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
