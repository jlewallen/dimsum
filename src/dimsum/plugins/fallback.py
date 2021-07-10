import logging
from typing import Type

import grammars
import transformers
from model import *

log = logging.getLogger("dimsum")


@grammars.grammar()
class Grammar(grammars.Grammar):
    @property
    def order(self) -> int:
        return grammars.LOWEST

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
