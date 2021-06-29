from typing import TextIO, Any

import logging
import sshd

import model.domains as domains
import model.scopes as scopes
import model.properties as properties
import model.world as world
import model.library as library

import bus
import visual
import config
import grammars

import plugins.all
import plugins.default

import cli.handlers as handlers

log = logging.getLogger("dimsum.cli")


class Interactive(sshd.CommandHandler):
    def __init__(
        self,
        cfg: config.Configuration,
        username: str = None,
        subscriptions: bus.SubscriptionManager = None,
        comms: visual.Comms = None,
    ):
        super().__init__()
        assert comms
        assert subscriptions
        self.cfg = cfg
        self.l = grammars.create_parser()
        self.domain = cfg.make_domain(handlers=[handlers.create(comms)])
        self.username = username
        self.comms = comms
        assert self.username
        self.subscription = subscriptions.subscribe(self.username, self.write)

    async def write(self, item: Any, **kwargs):
        log.info("send-user: %s %s", self.username, item)

    async def create_player_if_necessary(self, session: domains.Session):
        world = await session.prepare()

        player = await session.materialize(key=self.username)
        if player:
            return world, player

        if session.registrar.empty():
            log.info("creating example world")
            generics, area = library.create_example_world(world)
            session.register(generics.all)
            await session.add_area(area)

        player = scopes.alive(
            key=self.username,
            creator=session.world,
            props=properties.Common(self.username, desc="A player"),
        )
        await session.perform(plugins.default.actions.Join(), player)

        assert session.world
        return session.world, player

    async def handle(self, line: str):
        log.info("handle: %s '%s'", self.username, line)

        with self.domain.session() as session:
            world, player = await self.create_player_if_necessary(session)
            tree, create_evaluator = self.l.parse(line.strip())
            tree_eval = create_evaluator(world, player)
            action = tree_eval.transform(tree)
            reply = await session.perform(action, player)

            log.debug("reply: %s", reply)

            if isinstance(reply, visual.Renderable):
                await self.comms.user(reply)
            else:
                log.warning("unrenderable reply")

            await session.save()

    async def finished(self):
        self.subscription.remove()
