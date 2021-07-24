import asyncio
import uvicorn
import time
import shortuuid
import asyncclick as click
import ariadne.asgi
from datetime import datetime
from typing import List, Optional
from starlette.middleware.cors import CORSMiddleware
from ariadne.contrib.tracing.apollotracing import ApolloTracingExtension

from loggers import get_logger, get_noise_logger, setup_logging_queue
import config
import domains
import sshd
import schema as schema_factory
import migration

import everything  # noqa

import cli.interactive as interactive

log = get_logger("dimsum.cli")


async def servicing(domain: domains.Domain):
    first = True
    while True:
        try:
            try:
                now = datetime.now()
                if first or (domain.scheduled and now >= domain.scheduled.when):
                    with domain.session() as session:
                        await session.prepare()
                        await session.service(now, scheduled=domain.scheduled)
                        await session.save()
                    first = False
                else:
                    if domain.scheduled:
                        get_noise_logger().info(
                            "servicing: schedule=%s %s",
                            domain.scheduled,
                            domain.scheduled.when - now,
                        )
            except:
                log.exception("error", exc_info=True)
            await asyncio.sleep(1)
        except asyncio.exceptions.CancelledError:
            return


async def ticks(domain: domains.Domain):
    while True:
        try:
            await asyncio.sleep(60)
            try:
                with domain.session() as session:
                    await session.prepare()
                    now = datetime.now()
                    await session.tick(now)
                    await session.service(now)
                    await session.save()
            except:
                log.exception("error", exc_info=True)
        except asyncio.exceptions.CancelledError:
            return


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
    "--session-key",
    default=None,
    help="Session key.",
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
@click.option(
    "--unix-socket",
    help="Bind to a UNIX soket.",
)
async def server(
    database: str,
    session_key: Optional[str],
    conf: str,
    read: List[str],
    write: List[str],
    web_port: int,
    ssh_port: int,
    user: List[str],
    unix_socket: Optional[str],
):
    """
    Serve a database.
    """

    setup_logging_queue()

    cfg = config.symmetrical(database or ":memory:")
    if conf:
        cfg = config.get(conf)
    if read or write:
        cfg = config.Configuration(
            persistence=config.Persistence(read=read, write=write),
            session_key=session_key or config.generate_session_key(),
        )
    else:
        cfg.session_key = session_key or config.generate_session_key()

    domain = cfg.make_domain()
    with domain.session() as session:
        m = migration.Migrator(domain)
        await m.migrate(session)
        await session.save()

    schema = schema_factory.create()
    gql_app = ariadne.asgi.GraphQL(
        schema,
        context_value=schema_factory.context(cfg, domain),
        extensions=[ApolloTracingExtension],
        debug=True,
    )

    app = CORSMiddleware(
        gql_app,
        allow_origins=["*"],
        allow_methods=("GET", "POST", "OPTIONS"),
        allow_headers=["access-control-allow-origin", "authorization", "content-type"],
    )

    def create_ssh_session(**kwargs):
        return interactive.Interactive(domain, **kwargs)

    if user:
        temp = interactive.InitializeWorld(domain)
        await temp.initialize(user, key=lambda username: shortuuid.uuid(name=username))

    loop = asyncio.get_event_loop()
    gql_config = (
        uvicorn.Config(app=app, loop=loop, uds=unix_socket)
        if unix_socket
        else uvicorn.Config(app=app, loop=loop, port=web_port)
    )
    gql_server = uvicorn.Server(gql_config)
    gql_task = loop.create_task(gql_server.serve())
    sshd_task = loop.create_task(sshd.start_server(ssh_port, create_ssh_session))
    tick_task = loop.create_task(ticks(domain))
    servicing_task = loop.create_task(servicing(domain))
    await asyncio.gather(sshd_task, gql_task)

    tick_task.cancel()
    servicing_task.cancel()

    await asyncio.gather(tick_task, servicing_task)


# with proxy.start(
#     ["--enable-web-server"],
#     hostname=ipaddress.IPv4Address("0.0.0.0"),
#     port=8899,
#     plugins=[proxy.plugin.ReverseProxyPlugin],
# ):
#     pass
