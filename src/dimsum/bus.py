import inspect
import dataclasses
import asyncio
import functools
from typing import Any, Callable, Dict, List, Union, Awaitable

from loggers import get_logger
from model import Event, Comms, Renderable


@dataclasses.dataclass
class Subscription:
    manager: "SubscriptionManager"
    path_key: str
    handler: Callable[["Renderable"], Awaitable[None]]

    async def write(self, item: Renderable):
        await self.handler(item)

    def remove(self):
        self.manager._remove(self)


@dataclasses.dataclass
class SubscriptionManager(Comms):
    by_key: Dict[str, List[Subscription]] = dataclasses.field(default_factory=dict)

    def subscribe(self, path_key: str, handler_fn: Callable) -> Subscription:
        subscription = Subscription(self, path_key, handler_fn)
        self.by_key.setdefault(path_key, []).append(subscription)
        self._log.info("subscribed: %s", path_key)
        return subscription

    def _remove(self, subscription: Subscription) -> bool:
        assert subscription.path_key in self.by_key
        for_key = self.by_key[subscription.path_key]
        if subscription in for_key:
            for_key.remove(subscription)
            self._log.info("unsubscribed: %s", subscription.path_key)
            return True
        else:
            return False

    async def somebody(self, key: str, r: Renderable) -> bool:
        if key in self.by_key:
            await asyncio.gather(
                *[subscription.write(r) for subscription in self.by_key[key]]
            )
            return True
        return False

    async def everybody(self, r: Renderable) -> bool:
        await asyncio.gather(
            flatten(
                *[[sub.write(r) for sub in other] for key, other in self.by_key.items()]
            )
        )
        return True

    @functools.cached_property
    def _log(self):
        return get_logger("dimsum.bus.subscriptions")


class EventBus:
    def __init__(self, handlers=None):
        super().__init__()
        self.handlers = {}
        self.modules = [f(self) for f in handlers] if handlers else []

    def handler(self, klass):
        """Decorator for marking handlers of Events"""

        def final_decorator(func, **kwargs):
            self._log.debug("add handler for %s (%s)", klass, func)
            if klass not in self.handlers:
                self.handlers[klass] = []
            self.handlers[klass].append(func)

        return final_decorator

    async def publish(self, event: Event, **kwargs):
        assert event
        self._log.info("publish: %s", event)
        await self._invoke_handlers(event)

    async def _invoke_handlers(self, event: Union[Any]):
        for t in inspect.getmro(type(event)):
            await self._invoke_handler_type(t, event)

    async def _invoke_handler_type(self, klass, event: Union[Any]):
        if klass in self.handlers:
            handlers = self.handlers[klass]
            for fn in handlers:
                await fn(event=event)

    @functools.cached_property
    def _log(self):
        return get_logger("dimsum.bus.publish")


def flatten(l):
    return [item for sl in l for item in sl]
