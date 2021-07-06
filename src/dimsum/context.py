from typing import Optional, List, Any

import logging
import datetime
import abc
import contextvars

import model.entity as entity

worldCtx: Any = contextvars.ContextVar("dimsum:ctx")
log = logging.getLogger("dimsum")


class Ctx:
    @abc.abstractmethod
    def register(self, entity: entity.Entity) -> entity.Entity:
        raise NotImplementedError

    @abc.abstractmethod
    def unregister(self, entity: entity.Entity) -> entity.Entity:
        raise NotImplementedError

    @abc.abstractmethod
    async def publish(self, *args, **kwargs):
        raise NotImplementedError

    @abc.abstractmethod
    async def standard(self, klass, *args, **kwargs):
        raise NotImplementedError

    @abc.abstractmethod
    async def hook(self, name: str) -> None:
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
    ctx = worldCtx.get()
    assert ctx
    return ctx


def set(ctx: Optional[Ctx]):
    worldCtx.set(ctx)
