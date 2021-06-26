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
import model.scopes as scopes
import model.properties as properties
import model.world as world
import model.library as library
import grammars
import default

log = logging.getLogger("dimsum-cli")


@click.group()
def commands():
    pass


class SecureSession(sshd.CommandHandler):
    def __init__(self, cfg: config.Configuration, username: str = None):
        super().__init__()
        self.cfg = cfg
        self.domain = cfg.make_domain()
        self.username = username
        self.l = grammars.create_parser()

    async def create_player_if_necessary(self, session: domains.Session):
        player = await session.materialize(key=self.username)
        if player:
            return session.world, player

        if session.registrar.empty():
            log.info("creating example world")
            world = await session.prepare()
            generics, area = library.create_example_world(world)
            session.registrar.add_entities(generics.all)
            await session.add_area(area)

        player = scopes.alive(
            key=self.username,
            creator=session.world,
            props=properties.Common(self.username, desc="A player"),
        )
        await session.perform(default.actions.Join(), player)

        assert session.world
        return session.world, player

    async def handle(self, line: str, back: TextIO):
        log.info("handle: %s '%s'", self.username, line)

        with self.domain.session() as session:
            world, player = await self.create_player_if_necessary(session)
            tree, create_evaluator = self.l.parse(line.strip())
            tree_eval = create_evaluator(world, player)
            action = tree_eval.transform(tree)
            reply = await session.perform(action, player)

            log.info("reply: %s", reply)

            back.write(str(reply))

            await session.save()


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
        return SecureSession(cfg, username)

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
