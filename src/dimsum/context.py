from typing import Optional, List, Any
import logging
import datetime
import abc
import entity
import contextvars

worldCtx: Any = contextvars.ContextVar("diimsum:ctx")


class Ctx:
    @abc.abstractmethod
    def registrar(self) -> entity.Registrar:
        raise NotImplementedError

    @abc.abstractmethod
    async def publish(self, *args, **kwargs):
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
    def find_item(self, **kwargs) -> Optional[entity.Entity]:
        raise NotImplementedError


def get():
    return worldCtx.get()


def set(ctx: Ctx):
    worldCtx.set(ctx)


class FindItemMixin:
    def find_item_under(self, **kwargs) -> Optional[entity.Entity]:
        return get().find_item(candidates=self.gather_entities(), **kwargs)

    @abc.abstractmethod
    def gather_entities(self) -> List[entity.Entity]:
        raise NotImplementedError
