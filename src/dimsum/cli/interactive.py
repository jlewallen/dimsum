from typing import TextIO, Any, List

import logging
import sshd

import model.domains as domains
import model.scopes as scopes
import model.properties as properties
import model.world as world
import model.library as library
import model.visual as visual

import bus
import config
import grammars

import plugins.default

import handlers

import everything

log = logging.getLogger("dimsum.cli")


class InitializeWorld:
    def __init__(
        self,
        cfg: config.Configuration,
        subscriptions: bus.SubscriptionManager = None,
        comms: visual.Comms = None,
    ):
        assert comms
        self.cfg = cfg
        self.domain = cfg.make_domain(handlers=[handlers.create(comms)])

    async def create_player_if_necessary(self, session: domains.Session, key: str):
        world = await session.prepare()

        player = await session.materialize(key=key)
        if player:
            return world, player

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
        await session.perform(plugins.default.actions.Join(), player)
        await session.perform(plugins.default.actions.Auth(password="asdfasdf"), player)

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
        cfg: config.Configuration,
        username: str = None,
        subscriptions: bus.SubscriptionManager = None,
        comms: visual.Comms = None,
        channel: TextIO = None,
    ):
        super().__init__()
        assert username
        assert subscriptions
        assert comms
        assert channel
        self.cfg = cfg
        self.username = username
        self.comms = comms
        self.channel = channel
        self.l = grammars.create_parser()
        self.domain = cfg.make_domain(handlers=[handlers.create(comms)])
        self.subscription = subscriptions.subscribe(self.username, self.write)
        self.initialize = InitializeWorld(cfg, subscriptions, comms)

    async def write(self, item: visual.Renderable, **kwargs):
        self.channel.write("\n" + str(item.render_string()) + "\n\n")

    async def handle(self, line: str):
        log.info("handle: %s '%s'", self.username, line)

        with self.domain.session() as session:
            world, player = await self.initialize.create_player_if_necessary(
                session, self.username
            )
            tree, create_evaluator = self.l.parse(line.strip())
            tree_eval = create_evaluator(world, player)
            action = tree_eval.transform(tree)
            reply = await session.perform(action, player)

            log.debug("reply: %s", reply)

            if isinstance(reply, visual.Renderable):
                await self.write(reply)
            else:
                await self.write(visual.String(str(reply)))

            await session.save()

    async def finished(self):
        self.subscription.remove()
