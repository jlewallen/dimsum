from typing import Callable, List, Dict, Optional, Any

import logging
import dataclasses
import ast

import lark
import grammars

import model.game as game
import model.world as world
import model.entity as entity

import transformers

log = logging.getLogger("dimsum.dynamic")


@dataclasses.dataclass(frozen=True)
class Registered:
    prose: str
    handler: Callable


@dataclasses.dataclass
class SimplifiedAction(game.Action):
    entity: entity.Entity
    registered: Registered
    args: List[Any]

    async def perform(self, **kwargs):
        return self.registered.handler(self.entity, *self.args)


@dataclasses.dataclass
class SimplifiedTransformer(transformers.Base):
    registered: Registered
    entity: entity.Entity

    def start(self, args):
        return SimplifiedAction(self.entity, self.registered, args)


class Simplified:
    def __init__(self):
        self.registered: List[Registered] = []

    def language(self, prose: str):
        def wrap(fn):
            log.info("prose: '%s' %s", prose, fn)
            self.registered.append(Registered(prose, fn))
            return fn

        return wrap

    def evaluate(
        self,
        w: world.World,
        player: entity.Entity,
        entity: entity.Entity,
        command: str,
    ) -> Optional[game.Action]:
        for registered in self.registered:

            def transformer_factory(**kwargs):
                return SimplifiedTransformer(
                    registered=registered, entity=entity, world=w, player=player
                )

            evaluator = grammars.GrammarEvaluator(registered.prose, transformer_factory)

            action = evaluator.evaluate(command)
            if action:
                return action

        return None
