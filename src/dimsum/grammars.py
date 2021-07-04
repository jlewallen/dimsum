from typing import List, Type, Optional, Sequence, Callable

import abc
import logging
import functools
import dataclasses

from lark import Lark, exceptions, Transformer, Tree

import model.game as game

log = logging.getLogger("dimsum.grammars")


class ParsingException(Exception):
    pass


class CommandEvaluator:
    @abc.abstractmethod
    def evaluate(self, command: str, **kwargs) -> Optional[game.Action]:
        raise NotImplementedError


@dataclasses.dataclass
class PrioritizedEvaluator(CommandEvaluator):
    evaluators: Sequence[CommandEvaluator]

    def evaluate(self, command: str, **kwargs) -> Optional[game.Action]:
        for evaluator in self.evaluators:
            action = evaluator.evaluate(command, **kwargs)
            if action:
                return action
        return None


class Grammar:
    @property
    def order(self) -> int:
        return 1

    @property
    def transformer_factory(self) -> Type[Transformer]:
        raise NotImplementedError

    @property
    def lark(self) -> str:
        raise NotImplementedError


@dataclasses.dataclass
class GrammarEvaluator(CommandEvaluator):
    grammar: str
    transformer_factory: Callable

    @functools.cached_property
    def _parser(self) -> Lark:
        return _wrap_parser(self.grammar)

    def evaluate(self, command: str, **kwargs) -> Optional[game.Action]:
        try:
            tree = self._parser.parse(command)
            log.debug("parsed=%s", tree)
            if tree:
                transformer = self.transformer_factory(**kwargs)
                return transformer.transform(tree)
        except exceptions.UnexpectedCharacters:
            log.debug("parse-failed")
        except exceptions.UnexpectedEOF:
            log.debug("parse-failed")
        return None


grammars: List[Grammar] = []


def grammar():
    def wrap(klass):
        log.info("registered: %s", klass)
        grammars.append(klass())

    return wrap


def create_static_evaluator():
    log.info("static-evaluator: grammars=%s", grammars)
    return PrioritizedEvaluator(
        [GrammarEvaluator(g.lark, g.transformer_factory) for g in grammars]
    )


@functools.lru_cache
def _wrap_parser(custom: str) -> Lark:
    return Lark(
        """
        {0}

        DIRECTION:         "north" | "west" | "east" | "south"
        direction:         DIRECTION

        named_route:       USEFUL_WORD
        find_direction:    direction
        find_route_by_gid: object_by_gid
        route:             find_route_by_gid | find_direction | named_route

        makeable_noun:     TEXT
        contained_noun:    USEFUL_WORD+
        unheld_noun:       USEFUL_WORD+
        held_noun:         USEFUL_WORD+
        consumable_noun:   USEFUL_WORD+
        general_noun:      USEFUL_WORD+

        makeable:          makeable_noun
        contained:         object_by_gid | contained_noun
        consumable:        object_by_gid | consumable_noun
        unheld:            object_by_gid | unheld_noun
        held:              object_by_gid | held_noun
        noun:              object_by_gid | general_noun

        object_by_gid:     "#"NUMBER

        this:              "this"
        that:              "that"

        USEFUL_WORD:      /(?!(on|from|in|under|with|over|within|inside)\b)[a-zA-Z][a-zA-Z0-9]*/i

        CONSUMABLE_FIELDS: "sugar" | "fat" | "protein" | "toxicity" | "caffeine" | "alcohol" | "nutrition" | "vitamins"
        NUMERIC_FIELD:     "size" | "weight" | "volatility" | "explosivity" | CONSUMABLE_FIELDS
        TEXT_FIELD:        "name" | "desc" | "presence"

        TEXT_INNER:   (WORD | "?" | "!" | "." | "," | "'" | "`" | "$" | "%" | "#")
        TEXT:         TEXT_INNER (WS | TEXT_INNER)*
        NAME:         TEXT
        number:       NUMBER
        text:         TEXT
        _WS:          WS

        DOUBLE_QUOTED_STRING:  /"[^"]*"/
        SINGLE_QUOTED_STRING:  /'[^']*'/
        quoted_string:         SINGLE_QUOTED_STRING | DOUBLE_QUOTED_STRING
        string:                (WORD | quoted_string)

        %import common.WS
        %import common.WORD
        %import common.NUMBER
        %ignore " "
        """.format(
            custom
        )
    )
