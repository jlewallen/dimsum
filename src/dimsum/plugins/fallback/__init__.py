from typing import Any, List, Type

import logging

import model.properties as properties

import grammars

from plugins.actions import *
from context import *

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


class Evaluator(Evaluator):
    def verb(self, args):
        return Unknown()
