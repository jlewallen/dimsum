from typing import TextIO, List

import logging
import asyncclick as click
import asyncio
import ipaddress

import proxy

import ariadne.asgi
import uvicorn

from ariadne.contrib.tracing.apollotracing import ApolloTracingExtension
from starlette.middleware.cors import CORSMiddleware

import config
import schema as schema_factory
import bus
import sshd

import cli.interactive as interactive

log = logging.getLogger("dimsum.cli")


@click.group()
def commands():
    pass


@commands.command()
@click.option(
    "--database",
    help="Database file.",
    type=click.Path(),
)
@click.option(
    "--conf",
    help="Configuration file.",
    type=click.Path(exists=True),
)
@click.option(
    "--read",
    multiple=True,
    help="Read URLs.",
)
@click.option(
    "--write",
    multiple=True,
    help="Write URLs.",
)
@click.option(
    "--web-port",
    default=5100,
    help="Port.",
)
@click.option(
    "--ssh-port",
    default=5101,
    help="Port.",
)
@click.option(
    "--user",
    multiple=True,
    help="User to create.",
)
async def server(
    database: str,
    conf: str,
    read: List[str],
    write: List[str],
    web_port: int,
    ssh_port: int,
    user: List[str],
):
    """
    Serve a database.
    """

    cfg = config.symmetrical(database or ":memory")
    if conf:
        cfg = config.get(conf)
    if read or write:
        cfg = config.Configuration(
            persistence=config.Persistence(read=read, write=write),
            session_key=config.generate_session_key(),
        )

    subscriptions = bus.SubscriptionManager()
    schema = schema_factory.create()
    gql_app = ariadne.asgi.GraphQL(
        schema,
        context_value=schema_factory.context(cfg, subscriptions, subscriptions),
        debug=True,
        # extensions=[],
        extensions=[ApolloTracingExtension],
    )

    app = CORSMiddleware(
        gql_app,
        allow_origins=["*"],
        allow_methods=("GET", "POST", "OPTIONS"),
        allow_headers=["access-control-allow-origin", "authorization", "content-type"],
    )

    def create_ssh_session(**kwargs):
        return interactive.Interactive(
            cfg, subscriptions=subscriptions, comms=subscriptions, **kwargs
        )

    if user:
        for key in user:
            temp = interactive.InitializeWorld(
                cfg, subscriptions=subscriptions, comms=subscriptions
            )
            await temp.initialize(user)

    if False:
        with proxy.start(
            ["--enable-web-server"],
            hostname=ipaddress.IPv4Address("0.0.0.0"),
            port=8899,
            plugins=[proxy.plugin.ReverseProxyPlugin],
        ):
            pass

    loop = asyncio.get_event_loop()
    gql_config = uvicorn.Config(app=app, loop=loop, port=web_port)
    gql_server = uvicorn.Server(gql_config)
    gql_task = loop.create_task(gql_server.serve())
    sshd_task = loop.create_task(sshd.start_server(ssh_port, create_ssh_session))
    await asyncio.gather(sshd_task, gql_task)
