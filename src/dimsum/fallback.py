from typing import Any, List, Type

import logging

import grammar
import evaluator

import properties
import movement
import actions

log = logging.getLogger("dimsum")


@grammar.grammar()
class Grammar(grammar.Grammar):
    @property
    def order(self) -> int:
        return 65536

    @property
    def evaluator(self) -> Type[evaluator.Evaluator]:
        return Evaluator

    @property
    def lark(self) -> str:
        return """
        start:             verb
        verb:              WORD (this | that | noun)?
"""


class Evaluator(evaluator.Evaluator):
    def verb(self, args):
        return actions.Unknown()
