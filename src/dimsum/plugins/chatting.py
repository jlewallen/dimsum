import dataclasses
import logging
from typing import Dict, Optional, Type

from context import *
import grammars
from model.entity import *
from model.events import *
from model.game import *
from model.reply import *
from model.world import *
from finders import *
import scopes.occupyable as occupyable
from plugins.actions import *
import transformers

log = logging.getLogger("dimsum")


@event
@dataclasses.dataclass(frozen=True)
class PlayerSpoke(StandardEvent):
    message: str

    def render_string(self) -> Dict[str, str]:
        return {"text": f"{self.living.props.name} said '{self.message}'"}


@event
class PlayerTold(PlayerSpoke):
    def render_string(self) -> Dict[str, str]:
        return {"text": f"{self.living.props.name} whispered '{self.message}'"}


class Say(PersonAction):
    def __init__(self, message: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        assert message
        self.message = message

    async def perform(
        self, world: World, area: Entity, person: Entity, ctx: Ctx, **kwargs
    ):
        with area.make_and_discard(occupyable.Occupyable) as here:
            await ctx.publish(
                PlayerSpoke(
                    living=person, area=area, heard=here.occupied, message=self.message
                )
            )
        return Success()


class Tell(PersonAction):
    def __init__(
        self, who: Optional[ItemFinder] = None, message: Optional[str] = None, **kwargs
    ):
        super().__init__(**kwargs)
        assert who
        assert message
        self.who = who
        self.message = message

    async def perform(
        self, world: World, area: Entity, person: Entity, ctx: Ctx, **kwargs
    ):
        who = await world.apply_item_finder(person, self.who)
        if who:
            await ctx.publish(
                PlayerTold(living=person, area=area, heard=[who], message=self.message)
            )
            return Success("told")
        return Failure("who?")


@grammars.grammar()
class Grammar(grammars.Grammar):
    @property
    def order(self) -> int:
        return grammars.CHATTING

    @property
    def transformer_factory(self) -> Type[transformers.Base]:
        return Transformer

    @property
    def lark(self) -> str:
        return """
        start:             say | tell

        say:               ("say" | "\\"") TEXT
        tell:              "tell" noun TEXT
"""


class Transformer(transformers.Base):
    def say(self, args):
        return Say(str(args[0]))

    def tell(self, args):
        return Tell(args[0], str(args[1]))
