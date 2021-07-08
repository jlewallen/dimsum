import logging
from typing import Type

import grammars
import plugins.default.transformer as transformer
import transformers

log = logging.getLogger("dimsum")


@grammars.grammar()
class DefaultGrammar(grammars.Grammar):
    @property
    def transformer_factory(self) -> Type[transformers.Base]:
        return transformer.Default

    @property
    def lark(self) -> str:
        return """
        start:             modify

        modify:            "modify" TEXT_FIELD text                -> modify_field
                         | "modify" NUMERIC_FIELD number           -> modify_field
                         | "modify" "hard" "to" "see"              -> modify_hard_to_see
                         | "modify" "easy" "to" "see"              -> modify_easy_to_see
"""
