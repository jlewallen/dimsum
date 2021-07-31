import abc
import dataclasses
import functools
from typing import Callable, List, Optional, Sequence, Type
from lark import exceptions, Lark, Transformer

from loggers import get_logger
from model import Action

log = get_logger("dimsum.grammars")

HIGHEST = 0
CHATTING = 10
DYNAMIC = 50
LOWEST = 100


class CommandEvaluator:
    @property
    def order(self) -> int:
        return DYNAMIC + 1

    @abc.abstractmethod
    async def evaluate(self, command: str, **kwargs) -> Optional[Action]:
        raise NotImplementedError


class AlwaysUnknown(CommandEvaluator):
    @abc.abstractmethod
    async def evaluate(self, command: str, **kwargs) -> Optional[Action]:
        raise NotImplementedError


@dataclasses.dataclass
class PrioritizedEvaluator(CommandEvaluator):
    evaluators: Sequence[CommandEvaluator]

    def __post_init__(self):
        self.evaluators = sorted(self.evaluators, key=lambda e: e.order)

    async def evaluate(self, command: str, **kwargs) -> Optional[Action]:
        for evaluator in self.evaluators:
            action = await evaluator.evaluate(command, **kwargs)
            if action:
                return action
        return None


@dataclasses.dataclass
class LazyCommandEvaluator(CommandEvaluator):
    factory: Callable
    gorder: int = DYNAMIC

    @functools.cached_property
    def evaluator(self) -> CommandEvaluator:
        return PrioritizedEvaluator(self.factory())

    async def evaluate(self, command: str, **kwargs) -> Optional[Action]:
        return await self.evaluator.evaluate(command, **kwargs)


class ParsingException(Exception):
    pass


class Grammar:
    @property
    def order(self) -> int:
        return DYNAMIC + 1

    @property
    def transformer_factory(self) -> Type[Transformer]:
        raise NotImplementedError

    @property
    def lark(self) -> str:
        raise NotImplementedError


@dataclasses.dataclass
class GrammarEvaluator(CommandEvaluator):
    gorder: int
    grammar: str = dataclasses.field(repr=False)
    transformer_factory: Callable

    @property
    def order(self) -> int:
        return self.gorder

    @functools.cached_property
    def _parser(self) -> Lark:
        return _wrap_parser(self.grammar)

    async def evaluate(self, command: str, **kwargs) -> Optional[Action]:
        try:
            tree = self._parser.parse(command)
            log.info("parsed: %s", tree)
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
        log.debug("registered: %s", klass)
        grammars.append(klass())
        return klass

    return wrap


def create_static_evaluators():
    log.debug("static-evaluator: grammars=%s", grammars)
    return [GrammarEvaluator(g.order, g.lark, g.transformer_factory) for g in grammars]


@functools.lru_cache
def _wrap_parser(custom: str) -> Lark:
    return Lark(
        """
        {0}

        // Decreasing specificity is important here.
        DIRECTION:         "northeast" | "northwest" | "north" | "southwest" | "southeast" | "south" | "west" | "east" | "se" | "nw" | "sw" | "ne"
        direction:         DIRECTION

        named_route:       USEFUL_WORD+
        find_direction:    direction
        find_route_by_gid: object_by_gid
        route:             find_route_by_gid | find_direction | named_route

        makeable_noun:     TEXT
        contained_noun:    USEFUL_WORD
        unheld_noun:       USEFUL_WORD
        held_noun:         USEFUL_WORD
        consumable_noun:   USEFUL_WORD
        general_noun:      USEFUL_WORD

        makeable:          makeable_noun
        contained:         object_by_gid | contained_noun
        consumable:        object_by_gid | consumable_noun
        unheld:            object_by_gid | unheld_noun
        held:              object_by_gid | held_noun
        noun:              object_by_gid | myself | general_noun

        object_by_gid:     "#"NUMBER

        here:              "here"
        this:              "this"
        that:              "that"
        myself:            "myself"

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
