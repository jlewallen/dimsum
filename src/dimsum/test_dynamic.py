from typing import Callable, List, Dict, Optional, Any

import sys
import logging
import dataclasses
import pytest

import model.game as game
import model.properties as properties
import model.world as world
import model.entity as entity
import model.reply as reply

import model.scopes.mechanics as mechanics
import model.scopes.carryable as carryable
import model.scopes.behavior as behavior
import model.scopes as scopes

import plugins.actions as actions
import plugins.evaluation as evaluation

import test

log = logging.getLogger("dimsum.tests")

import grammars
import ast
from test_decoration import Hooks, Hello


@dataclasses.dataclass(frozen=True)
class Registered:
    prose: str
    handler: Callable


@dataclasses.dataclass(frozen=True)
class Available:
    registered: Registered
    parser: Callable


from lark import exceptions


@dataclasses.dataclass
class SimplifiedAction(actions.PersonAction):
    entity: entity.Entity
    registered: Registered
    args: List[Any]

    async def perform(self, **kwargs):
        return self.registered.handler(self.entity, *self.args)


@dataclasses.dataclass
class SimplifiedEvaluator(evaluation.BaseEvaluator):
    entity: entity.Entity
    registered: Registered

    def start(self, args):
        return SimplifiedAction(self.entity, self.registered, args)


@dataclasses.dataclass
class Evaluatable:
    handler: Callable
    args: List[Any]


class Simplified:
    def __init__(self):
        self.registered = []
        self.available = []

    def language(self, prose: str):
        def wrap(fn):
            log.info("prose: '%s' %s", prose, fn)
            self.registered.append(Registered(prose, fn))
            return fn

        return wrap

    def create_lark_grammar(self, prose: str):
        # TODO Simplify these one liners via another lark step.
        return prose

    def initialize(self):
        self.available = []
        for registered in self.registered:
            simple_grammar = self.create_lark_grammar(registered.prose)
            parser = grammars.wrap_parser(simple_grammar)
            self.available.append(Available(registered, parser))

    def parse(self, text: str):
        if len(self.available) != len(self.registered):  # TODO weak
            self.initialize()

        log.debug("parsing '%s'", text)
        for a in self.available:
            try:
                tree = a.parser.parse(text)
                return tree, a.registered
            except exceptions.UnexpectedCharacters:
                log.debug("parse-failed: '%s'", a.registered.prose)
            except exceptions.UnexpectedEOF:
                log.debug("parse-failed: '%s'", a.registered.prose)
        return None, None

    def evaluate(
        self,
        w: world.World,
        player: entity.Entity,
        entity: entity.Entity,
        text: str,
    ):
        tree, registered = self.parse(text)
        if tree is None:
            return None
        evaluator = SimplifiedEvaluator(w, player, entity, registered)
        log.debug("parsed: '%s' tree=%s", text, tree)
        action = evaluator.transform(tree)
        log.info("parsed: '%s' tree=%s args=%s", text, tree, action)
        return action


@pytest.mark.asyncio
async def test_idea(caplog):
    s = Simplified()

    @s.language('start: "wiggle"')
    def wiggle(entity):
        log.info("wiggle: %s", entity)

    @s.language('start: "burp"')
    def burp(entity):
        log.info("burp: %s", entity)

    tw = test.TestWorld()
    await tw.initialize()

    with tw.domain.session() as session:
        world = await session.prepare()
        jacob = await session.materialize(key=tw.jacob_key)
        thing = scopes.item(props=properties.Common(name="Thing", desc="Thing"))

        action = s.evaluate(world, jacob, thing, "wiggle")
        await session.perform(action, person=jacob)

        action = s.evaluate(world, jacob, thing, "burp")
        await session.perform(action, person=jacob)


@pytest.mark.asyncio
async def test_python_evaluate(caplog):
    tw = test.TestWorld()
    await tw.initialize()

    code = """
# Hello

# log.info("Hello!")
# for g in globals():
#    log.info("global: %s", g)

@link.wrap(Hello, Hello.yell)
def hello(name: str):
    log.info("saying Hello %s!", name)

# hello("inside")
"""

    linking = Hooks()
    gs = dict(log=log, link=linking, Hello=Hello)
    tree = ast.parse(code)
    compiled = compile(tree, filename="<ast>", mode="exec")
    eval(compiled, gs, dict())

    log.info("linking: %s", linking)
