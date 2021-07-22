import dataclasses
from typing import Type, Optional, List, Dict, Any

import grammars
import transformers
from loggers import get_logger
from model import *
from finders import *
from plugins.actions import PersonAction
import scopes.users as users

log = get_logger("dimsum")


class Chmod(PersonAction):
    def __init__(self, item: Optional[ItemFinder] = None, **kwargs):
        super().__init__(**kwargs)
        assert item
        self.item = item

    async def perform(
        self, world: World, area: Entity, person: Entity, ctx: Ctx, **kwargs
    ):
        item = await ctx.apply_item_finder(person, self.item)
        if not item:
            return Failure("chmod what?")

        return Success("Done!")


def make_table(rows: List[List[str]]) -> str:
    def prep(row: List[str]) -> str:
        return "| " + " | ".join(row) + " |"

    return "\n".join([prep(row) for row in rows])


@dataclasses.dataclass
class EntityChmods(Reply, Renderable):
    entity: Entity
    chmods: Dict[str, Acls]

    def render_tree(self) -> Dict[str, Any]:
        def render_acls(acls) -> str:
            return " ".join(
                [f"{acl.perm} {' '.join(acl.keys)}" for acl in acls.hydrated]
            )

        rows = [[key, render_acls(acls)] for key, acls in self.chmods.items()]
        return {
            "lines": [
                f"### {self.entity.props.described}",
                make_table([["Path", "Acls"], ["----", "----"]] + rows),
            ]
        }


class ChmodLs(PersonAction):
    def __init__(self, item: Optional[ItemFinder] = None, **kwargs):
        super().__init__(**kwargs)
        assert item
        self.item = item

    async def perform(
        self, world: World, area: Entity, person: Entity, ctx: Ctx, **kwargs
    ):
        item = await ctx.apply_item_finder(person, self.item)
        if not item:
            return Failure("chmod what?")

        original = ctx.session.registrar.get_original_if_available(  # type:ignore
            item.key
        )
        assert original

        acls = find_all_acls(original.compiled)

        return EntityChmods(item, acls)


class Transformer(transformers.Base):
    def chmod_entity_acl(self, args):
        log.info("hello")
        return Chmod(item=args[0])

    def chmod_path_acl(self, args):
        log.info("hello")
        return Chmod(item=args[0])

    def chmod_ls(self, args):
        return ChmodLs(item=args[0])


@grammars.grammar()
class ChmodGrammar(grammars.Grammar):
    @property
    def transformer_factory(self) -> Type[transformers.Base]:
        return Transformer

    @property
    def lark(self) -> str:
        return """
        start:             chmod

        chmod:             "chmod" noun                 -> chmod_ls
                         | "chmod" noun acl             -> chmod_entity_acl
                         | "chmod" noun PATH acl        -> chmod_path_acl

        acl:               permission identity
        permission:        ("write" | "read")
        identity:          ("$owner" | "$everybody" | "$system" | /[^\\S]+/i)

        PATH:              /[^\\S]+/i
"""
