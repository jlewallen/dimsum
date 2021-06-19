from typing import List, Type
from lark import Lark
from lark import exceptions
from lark import Transformer

import logging

log = logging.getLogger("dimsum")


class Grammar:
    @property
    def order(self) -> int:
        return 1

    @property
    def evaluator(self) -> Type[Transformer]:
        raise NotImplementedError

    @property
    def lark(self) -> str:
        raise NotImplementedError


grammars: List[Grammar] = []


def grammar():
    def wrap(klass):
        log.info("registered grammar: %s", klass)
        grammars.append(klass())

    return wrap


class ParseMultipleGrammars:
    def __init__(self, grammars):
        self.grammars = grammars
        self.parsers = [
            (wrap_parser(g.lark), g) for g in sorted(grammars, key=lambda g: g.order)
        ]

    def parse(self, command: str):
        for parser, grammar in self.parsers:
            try:
                tree = parser.parse(command)
                log.info("done %s", tree)
                if tree:
                    return tree, grammar.evaluator
            except exceptions.UnexpectedCharacters:
                log.debug("parse-failed")
        raise Exception("unable to parse")


def create_parser():
    log.info("create-parser: grammars=%s", grammars)

    return ParseMultipleGrammars(sorted(grammars, key=lambda g: g.order))


def wrap_parser(custom: str):
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
