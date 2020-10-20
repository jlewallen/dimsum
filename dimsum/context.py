from typing import Any
import logging
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
    def extend(self, **kwargs) -> "Ctx":
        raise NotImplementedError


def get():
    return worldCtx.get()


def set(ctx: Ctx):
    worldCtx.set(ctx)
