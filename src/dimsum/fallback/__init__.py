from typing import Any, List, Type

import logging

import model.properties as properties
import model.scopes.movement as movement

import default.evaluator as evaluator
import default.actions as actions

import grammars

log = logging.getLogger("dimsum")


@grammars.grammar()
class Grammar(grammars.Grammar):
    @property
    def order(self) -> int:
        return 65536

    @property
    def evaluator(self):
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
