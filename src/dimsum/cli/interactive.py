import logging
from typing import List, Optional, TextIO

import scopes
import domains
import library
import sshd
from model import *


from plugins.actions import Join
from plugins.admin import Auth, lookup_username, register_username

log = logging.getLogger("dimsum.cli")


class InitializeWorld:
    def __init__(self, domain: domains.Domain):
        self.domain: domains.Domain = domain

    async def create_player_if_necessary(self, session: domains.Session, username: str):
        world = await session.prepare()

        maybe_key = await lookup_username(world, username)
        if maybe_key:
            maybe_player = await session.try_materialize(key=maybe_key)
            if not maybe_player.empty():
                return world, maybe_player.one()

        if get_well_known_key(world, WelcomeAreaKey) is None:
            log.info("creating example world")
            generics, area = library.create_example_world(world)
            session.register(generics.all)
            await session.add_area(area)

        player = scopes.alive(
            creator=session.world,
            props=Common(name=username, desc="A player"),
        )
        await register_username(world, username, player.key)
        await session.perform(Join(), player)
        await session.perform(Auth(password="asdfasdf"), player)

        assert session.world
        return session.world, player

    async def initialize(self, users: List[str]):
        with self.domain.session() as session:
            for key in users:
                await self.create_player_if_necessary(session, key)
            await session.save()


class Interactive(sshd.CommandHandler):
    def __init__(
        self,
        domain: domains.Domain,
        username: Optional[str] = None,
        channel: Optional[TextIO] = None,
    ):
        super().__init__()
        assert username
        assert domain
        assert channel
        self.domain = domain
        self.username = username
        self.channel = channel
        self.subscription = self.domain.subscriptions.subscribe(
            self.username, self.write
        )
        self.initialize = InitializeWorld(self.domain)

    async def write(self, item: Renderable, **kwargs):
        self.channel.write("\n" + str(item.render_tree()) + "\n\n")

    async def handle(self, line: str):
        log.info("handle: %s '%s'", self.username, line)

        with self.domain.session() as session:
            world, player = await self.initialize.create_player_if_necessary(
                session, self.username
            )
            reply = await session.execute(player, line.strip())

            log.debug("reply: %s", reply)

            if isinstance(reply, Renderable):
                await self.write(reply)
            else:
                await self.write(String(str(reply)))

            await session.save()

    async def finished(self):
        self.subscription.remove()
