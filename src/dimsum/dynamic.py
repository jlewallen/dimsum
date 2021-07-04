from typing import Callable, List, Dict, Optional, Any

import logging
import dataclasses
import ast

from lark import exceptions
import grammars

import model.world as world
import model.entity as entity

import plugins.actions as actions
import plugins.evaluation as evaluation

log = logging.getLogger("dimsum.dynamic")


@dataclasses.dataclass(frozen=True)
class Registered:
    prose: str
    handler: Callable


@dataclasses.dataclass(frozen=True)
class Available:
    registered: Registered
    parser: Callable


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
    ) -> Optional[actions.PersonAction]:
        tree, registered = self.parse(text)
        if tree is None:
            return None
        evaluator = SimplifiedEvaluator(w, player, entity, registered)
        log.debug("parsed: '%s' tree=%s", text, tree)
        action = evaluator.transform(tree)
        log.info("parsed: '%s' tree=%s action=%s", text, tree, action)
        return action
