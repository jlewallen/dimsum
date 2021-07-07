import abc
import contextvars
import logging
from typing import Any, Optional

import model.entity as entity
import model.events as events

world_ctx: Any = contextvars.ContextVar("dimsum:ctx")
log = logging.getLogger("dimsum")


class Ctx:
    @abc.abstractmethod
    def register(self, entity: entity.Entity) -> entity.Entity:
        raise NotImplementedError

    @abc.abstractmethod
    def unregister(self, entity: entity.Entity) -> entity.Entity:
        raise NotImplementedError

    @abc.abstractmethod
    async def publish(self, ev: events.Event):
        raise NotImplementedError

    @abc.abstractmethod
    async def standard(self, klass, *args, **kwargs):
        raise NotImplementedError

    @abc.abstractmethod
    def create_item(self, **kwargs) -> entity.Entity:
        raise NotImplementedError

    @abc.abstractmethod
    def extend(self, **kwargs) -> "Ctx":
        raise NotImplementedError

    @abc.abstractmethod
    async def find_item(self, **kwargs) -> Optional[entity.Entity]:
        raise NotImplementedError


def get() -> Ctx:
    ctx = world_ctx.get()
    assert ctx
    return ctx


def set(ctx: Optional[Ctx]):
    world_ctx.set(ctx)
