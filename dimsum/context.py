import logging
import abc
import entity


class Ctx:
    @abc.abstractmethod
    def registry(self) -> entity.Registrar:
        raise NotImplementedError

    @abc.abstractmethod
    async def publish(self, **kwargs):
        raise NotImplementedError

    @abc.abstractmethod
    async def hook(self, name: str) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def extend(self, **kwargs) -> "Ctx":
        raise NotImplementedError
