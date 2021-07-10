import abc
import contextvars
import logging
from typing import Any, Optional

from .entity import Entity
from .events import Event
from .conditions import Condition

world_ctx: Any = contextvars.ContextVar("dimsum:ctx")
log = logging.getLogger("dimsum")


class Ctx:
    @abc.abstractmethod
    def register(self, entity: Entity) -> Entity:
        raise NotImplementedError

    @abc.abstractmethod
    def unregister(self, entity: Entity) -> Entity:
        raise NotImplementedError

    @abc.abstractmethod
    async def publish(self, ev: Event):
        raise NotImplementedError

    @abc.abstractmethod
    async def standard(self, klass, *args, **kwargs):
        raise NotImplementedError

    @abc.abstractmethod
    def create_item(self, **kwargs) -> Entity:
        raise NotImplementedError

    @abc.abstractmethod
    def extend(self, **kwargs) -> "Ctx":
        raise NotImplementedError

    @abc.abstractmethod
    async def find_item(self, **kwargs) -> Optional[Entity]:
        raise NotImplementedError

    @abc.abstractmethod
    def evaluate(self, condition: Condition) -> bool:
        raise NotImplementedError


def get() -> Ctx:
    ctx = world_ctx.get()
    assert ctx
    return ctx


def set(ctx: Optional[Ctx]):
    world_ctx.set(ctx)
