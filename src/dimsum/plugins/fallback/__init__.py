from typing import Any, List, Type

import logging

import model.properties as properties

import grammars
import transformers

from plugins.actions import *

from context import *

log = logging.getLogger("dimsum")


@grammars.grammar()
class Grammar(grammars.Grammar):
    @property
    def order(self) -> int:
        return 65536

    @property
    def transformer_factory(self) -> Type[transformers.Base]:
        return Transformer

    @property
    def lark(self) -> str:
        return """
        start:             verb
        verb:              WORD (this | that | noun)?
"""


class Transformer(transformers.Base):
    def verb(self, args):
        return Unknown()
