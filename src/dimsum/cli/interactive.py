from typing import TextIO

import logging
import sshd

import model.domains as domains
import model.scopes as scopes
import model.properties as properties
import model.world as world
import model.library as library
import grammars
import default
import config
import messages

log = logging.getLogger("dimsum.cli")


class Interactive(sshd.CommandHandler):
    def __init__(self, cfg: config.Configuration, username: str = None):
        super().__init__()
        self.cfg = cfg
        self.domain = cfg.make_domain()
        self.username = username
        self.l = grammars.create_parser()

    async def create_player_if_necessary(self, session: domains.Session):
        world = await session.prepare()

        player = await session.materialize(key=self.username)
        if player:
            return world, player

        if session.registrar.empty():
            log.info("creating example world")
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

            visitor = messages.ReplyVisitor()
            visual = reply.accept(visitor)
            log.info(
                "%s" % (visual),
            )

            back.write("\n")

            if "title" in visual:
                back.write(visual["title"])
                back.write("\n")

            if "text" in visual:
                back.write(visual["text"])
                back.write("\n")

            if "description" in visual:
                back.write("\n")
                back.write(visual["description"])

            back.write("\n")

            await session.save()
