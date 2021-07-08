import logging
from typing import List, Optional, TextIO

import model.domains as domains
import model.library as library
import model.properties as properties
import model.scopes as scopes
import model.visual as visual
import plugins.default
import sshd

log = logging.getLogger("dimsum.cli")


class InitializeWorld:
    def __init__(self, domain: domains.Domain):
        self.domain: domains.Domain = domain

    async def create_player_if_necessary(self, session: domains.Session, key: str):
        world = await session.prepare()

        maybe_player = await session.try_materialize(key=key)
        if not maybe_player.empty():
            return world, maybe_player.one()

        if world.welcome_area() is None:
            log.info("creating example world")
            generics, area = library.create_example_world(world)
            session.register(generics.all)
            await session.add_area(area)

        player = scopes.alive(
            key=key,
            creator=session.world,
            props=properties.Common(key, desc="A player"),
        )
        await session.perform(plugins.default.Join(), player)
        await session.perform(plugins.admin.Auth(password="asdfasdf"), player)

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

    async def write(self, item: visual.Renderable, **kwargs):
        self.channel.write("\n" + str(item.render_string()) + "\n\n")

    async def handle(self, line: str):
        log.info("handle: %s '%s'", self.username, line)

        with self.domain.session() as session:
            world, player = await self.initialize.create_player_if_necessary(
                session, self.username
            )
            reply = await session.execute(player, line.strip())

            log.debug("reply: %s", reply)

            if isinstance(reply, visual.Renderable):
                await self.write(reply)
            else:
                await self.write(visual.String(str(reply)))

            await session.save()

    async def finished(self):
        self.subscription.remove()
