import asyncio
import logging
from typing import List

import ariadne.asgi
from ariadne.contrib.tracing.apollotracing import ApolloTracingExtension
import asyncclick as click
import cli.interactive as interactive
import config
import everything  # noqa
import model.domains as domains
import schema as schema_factory
import sshd
from starlette.middleware.cors import CORSMiddleware
import uvicorn

log = logging.getLogger("dimsum.cli")


async def ticks(domain: domains.Domain):
    while True:
        try:
            await asyncio.sleep(60)
            try:
                with domain.session() as session:
                    await session.prepare()
                    await session.tick()
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

    domain = cfg.make_domain()
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
        for key in user:
            temp = interactive.InitializeWorld(domain)
            await temp.initialize(user)

    loop = asyncio.get_event_loop()
    gql_config = uvicorn.Config(app=app, loop=loop, port=web_port)
    gql_server = uvicorn.Server(gql_config)
    gql_task = loop.create_task(gql_server.serve())
    sshd_task = loop.create_task(sshd.start_server(ssh_port, create_ssh_session))
    tick_task = loop.create_task(ticks(domain))
    await asyncio.gather(sshd_task, gql_task)

    tick_task.cancel()

    await asyncio.gather(tick_task)


# with proxy.start(
#     ["--enable-web-server"],
#     hostname=ipaddress.IPv4Address("0.0.0.0"),
#     port=8899,
#     plugins=[proxy.plugin.ReverseProxyPlugin],
# ):
#     pass
