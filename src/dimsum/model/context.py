import abc
import contextvars
from typing import Any, Optional, List, Literal

from loggers import get_logger

from .entity import Entity
from .events import Event

world_ctx: Any = contextvars.ContextVar("dimsum:ctx", default=None)
log = get_logger("dimsum")


class MaterializeAndCreate:
    @abc.abstractmethod
    def find_by_key(self, key: str) -> Entity:
        raise NotImplementedError

    @abc.abstractmethod
    def create_item(self, **kwargs) -> Entity:
        raise NotImplementedError

    @abc.abstractmethod
    async def try_materialize_key(self, key: str) -> Optional[Entity]:
        raise NotImplementedError

    async def materialize_key(self, key: str) -> Optional[Entity]:
        e = await self.try_materialize_key(key)
        assert e
        return e


class Ctx(MaterializeAndCreate):
    @property
    def world(self) -> Entity:
        raise NotImplementedError

    @abc.abstractmethod
    def register(self, entity: Entity) -> Entity:
        raise NotImplementedError

    @abc.abstractmethod
    def unregister(self, entity: Entity) -> Entity:
        raise NotImplementedError

    @abc.abstractmethod
    def extend(self, **kwargs) -> "Ctx":
        raise NotImplementedError

    @abc.abstractmethod
    async def publish(self, ev: Event):
        raise NotImplementedError

    @abc.abstractmethod
    async def standard(self, klass, *args, **kwargs):
        raise NotImplementedError

    @abc.abstractmethod
    async def find_item(self, **kwargs) -> Optional[Entity]:
        raise NotImplementedError

    @abc.abstractmethod
    async def apply_item_finder(
        self, person: Entity, finder, **kwargs
    ) -> Optional[Entity]:
        raise NotImplementedError

    @abc.abstractmethod
    def __enter__(self) -> Any:
        raise NotImplementedError

    @abc.abstractmethod
    def __exit__(self, type, value, traceback) -> Literal[False]:
        raise NotImplementedError


def get() -> Ctx:
    ctx = world_ctx.get()
    assert ctx
    return ctx


def maybe_get() -> Optional[Ctx]:
    return world_ctx.get()


def set(ctx: Optional[Ctx]):
    world_ctx.set(ctx)
