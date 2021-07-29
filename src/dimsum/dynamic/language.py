import dataclasses
from typing import List, Union, Dict, Optional, Any

from model import (
    Entity,
    World,
    Ctx,
    Reply,
    Action,
    ItemFinder,
    Success,
    Failure,
    DynamicFailure,  # TODO move here?
)
from loggers import get_logger
import transformers

from .core import Registered

errors_log = get_logger("dimsum.dynamic.errors")


@dataclasses.dataclass(frozen=True)
class SimplifiedAction(Action):
    entity: Entity
    registered: Registered
    args: List[Any]

    def _transform_reply(self, r: Union[Reply, str]) -> Reply:
        if isinstance(r, str):
            return Success(r)
        return r

    async def _transform_arg(
        self, arg: ItemFinder, world: World, person: Entity, ctx: Ctx
    ) -> Optional[Entity]:
        assert isinstance(arg, ItemFinder)
        return await ctx.apply_item_finder(person, arg)

    async def _args(self, world: World, person: Entity, ctx: Ctx) -> List[Any]:
        return [await self._transform_arg(a, world, person, ctx) for a in self.args]

    async def perform(
        self,
        world: World,
        area: Entity,
        person: Entity,
        ctx: Ctx,
        **kwargs,
    ):
        try:
            args = await self._args(world, person, ctx)
            reply = await self.registered.handler(
                *args,
                this=self.entity,
                person=person,
                **kwargs,
            )
            if reply:
                return self._transform_reply(reply)
            return Failure("no reply from handler?")
        except Exception as e:
            errors_log.exception("handler:error", exc_info=True)
            return DynamicFailure(str(e), str(self.registered.handler))


@dataclasses.dataclass
class SimplifiedTransformer(transformers.Base):
    registered: Registered
    entity: Entity

    def start(self, args):
        return SimplifiedAction(self.entity, self.registered, args)
