from typing import List

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
import model.scopes.users as users
import model.scopes as scopes

import default.actions as actions

import bus
import grammars
import serializing
import luaproxy

import digging
import simple

log = logging.getLogger("dimsum.tests")


def create_empty_world():
    return world.World()


class TestWorld:
    def __init__(self):
        self.domain = domains.Domain()
        self.bus = self.domain.bus
        self.l = grammars.create_parser()

    def add_simple_area_here(self, door, name):
        with self.domain.session() as session:
            assert self.player
            door = scopes.item(creator=self.player, props=properties.Common(door))
            area = scopes.area(creator=self.player, props=properties.Common(name))
            with door.make(movement.Movement) as nav:
                nav.link_area(area)
            with self.area.make(carryable.Containing) as ground:
                ground.add_item(door)
            session.register(door)
            session.register(area)
            return area

    async def add_carla(self):
        log.info("adding carla")
        with self.domain.session() as session:
            world = await session.prepare()

            carla = scopes.alive(
                creator=world,
                props=properties.Common("Carla", desc="Chief Salad Officer."),
            )
            await session.perform(actions.Join(), carla)
            await session.save()
            return carla

    async def add_tomi(self):
        log.info("adding tomi")
        with self.domain.session() as session:
            world = await session.prepare()

            tomi = scopes.alive(
                creator=world,
                props=properties.Common("Tomi", desc="Chief Crying Officer."),
            )
            await session.perform(actions.Join(), tomi)
            await session.save()
            return tomi

    async def add_jacob(self):
        log.info("adding carla")
        with self.domain.session() as session:
            world = await session.prepare()

            jacob = scopes.alive(
                creator=world,
                props=properties.Common("Jacob", desc="Curly haired bastard."),
            )

            await session.perform(actions.Join(), jacob)
            await session.save()
            return jacob

    async def initialize(self, world=None, area=None, **kwargs):
        log.info("initialize")
        with self.domain.session() as session:
            if world:
                self.world = world
            else:
                world = await session.prepare()

            self.area = area

            if not self.area:
                self.area = scopes.area(
                    creator=world, props=properties.Common("Living room")
                )

            await session.add_area(self.area)
            await session.save()

        self.player = await self.add_jacob()

    def get_default_area(self):
        return self.area

    def add_item(self, item):
        self.domain.registrar.register(item)
        with self.area.make(carryable.Containing) as ground:
            ground.add_item(item)
        return item

    def dumps(self, item) -> str:
        return serializing.serialize(item, indent=4)

    async def execute(self, command: str, person=None, **kwargs):
        if not person:
            person = self.player
        log.info("executing: %s" % (command,))
        tree, create_evaluator = self.l.parse(command)
        log.info("parsed: %s" % (tree,))
        with self.domain.session() as session:
            tree_eval = create_evaluator(session.world, person)
            action = tree_eval.transform(tree)
            assert action
            assert isinstance(action, game.Action)

            response = await session.perform(action, person)
            log.info("response: %s" % (response,))
            await session.save()
        return response

    async def success(self, *commands: str, **kwargs):
        for command in commands:
            r = await self.execute(command, **kwargs)
            if not isinstance(r, game.Failure):
                return r
            log.error("reply: %s", r)
            assert not isinstance(r, game.Failure)

    async def failure(self, command: str, **kwargs):
        r = await self.execute(command, **kwargs)
        assert isinstance(r, game.Failure)
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
