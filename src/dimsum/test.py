from typing import List, Optional

import asyncio
import logging
import sys
import lark
import base64

import model.entity as entity
import model.properties as properties
import model.game as game
import model.world as world
import model.things as things
import model.reply as reply
import model.sugar as sugar
import model.domains as domains

import model.scopes.movement as movement
import model.scopes.carryable as carryable
import model.scopes.occupyable as occupyable
import model.scopes.users as users
import model.scopes as scopes

import bus
import grammars
import serializing
import luaproxy

import plugins.default.actions as actions

import everything

log = logging.getLogger("dimsum.tests")


def create_empty_world():
    return world.World()


class TestWorld:
    def __init__(self, handlers=None):
        self.domain = domains.Domain(handlers=handlers)
        self.l = grammars.create_parser()
        self.carla_key = None
        self.jacob_key = None
        self.tomi_key = None

    async def add_simple_area_here(self, door, name):
        with self.domain.session() as session:
            world = await session.prepare()
            door = scopes.item(creator=world, props=properties.Common(door))
            area = scopes.area(creator=world, props=properties.Common(name))
            with door.make(movement.Movement) as nav:
                nav.link_area(area)
            with area.make(carryable.Containing) as ground:
                ground.add_item(door)
            session.register(door)
            session.register(area)
            return area

    async def add_carla(self):
        if self.carla_key:
            return self.carla_key

        log.info("adding carla")
        with self.domain.session() as session:
            world = await session.prepare()

            carla = scopes.alive(
                creator=world,
                props=properties.Common("Carla", desc="Chief Salad Officer."),
            )
            await session.perform(actions.Join(), carla)
            await session.save()
            self.carla_key = carla.key
            return carla

    async def add_tomi(self):
        if self.tomi_key:
            return self.tomi_key

        log.info("adding tomi")
        with self.domain.session() as session:
            world = await session.prepare()

            tomi = scopes.alive(
                creator=world,
                props=properties.Common("Tomi", desc="Chief Crying Officer."),
            )
            await session.perform(actions.Join(), tomi)
            await session.save()
            self.tomi_key = tomi.key
            return tomi

    async def add_jacob(self):
        if self.jacob_key:
            return self.jacob_key

        log.info("adding jacob")
        with self.domain.session() as session:
            world = await session.prepare()

            jacob = scopes.alive(
                creator=world,
                props=properties.Common("Jacob", desc="Curly haired bastard."),
            )

            await session.perform(actions.Join(), jacob)
            await session.save()
            self.jacob_key = jacob.key
            return jacob

    async def initialize(self, world=None, area=None, **kwargs):
        log.info("initialize")
        with self.domain.session() as session:
            if world:
                self.world = world
            else:
                world = await session.prepare()

            if not area:
                area = scopes.area(
                    creator=world, props=properties.Common("Living room")
                )

            await session.add_area(area)
            await session.save()

        await self.add_jacob()

    def add_item_to_welcome_area(self, item, session=None):
        assert session
        session.register(item)
        with session.world.make(world.Welcoming) as welcoming:
            with welcoming.area.make(carryable.Containing) as ground:
                ground.add_item(item)
        return item

    def dumps(self, item) -> Optional[str]:
        return serializing.serialize(item, indent=4)

    async def execute(self, command: str, person=None, **kwargs):
        log.info("executing: %s" % (command,))
        tree, create_evaluator = self.l.parse(command)

        log.info("=" * 100)
        log.info("parsed: %s" % (tree,))
        log.info("=" * 100)

        with self.domain.session() as session:
            world = await session.prepare()

            tree_eval = create_evaluator(world, person)
            action = tree_eval.transform(tree)
            assert action
            assert isinstance(action, game.Action)

            assert self.jacob_key
            person = await session.materialize(
                key=self.jacob_key if person is None else person
            )
            response = await session.perform(action, person)

            log.info("response: %s" % (response,))
            if isinstance(response, reply.Failure):
                log.info("unsaved!")
            else:
                await session.save()

            return response

    async def success(self, *commands: str, **kwargs):
        for command in commands:
            r = await self.execute(command, **kwargs)
            if not isinstance(r, reply.Failure):
                return r
            log.error("reply: %s", r)
            assert not isinstance(r, reply.Failure)

    async def failure(self, command: str, **kwargs):
        r = await self.execute(command, **kwargs)
        assert isinstance(r, reply.Failure)
        return r


async def make_simple_domain(password: str = None, store=None) -> domains.Domain:
    domain = domains.Domain(store=store)
    with domain.session() as session:
        world = await session.prepare()

        welcome = scopes.area(
            key="welcome",
            props=properties.Common(name="welcome"),
            creator=world,
        )
        jacob_key = base64.b64encode("jlewallen".encode("utf-8")).decode("utf-8")
        jacob = scopes.alive(
            key=jacob_key, props=properties.Common(name="Jacob"), creator=world
        )

        if password:
            with jacob.make(users.Auth) as auth:
                auth.change(password)

        await session.add_area(welcome)
        session.register(jacob)
        await session.perform(actions.Join(), jacob)
        await session.save()

    return domain
