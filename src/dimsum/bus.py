from typing import Dict, Union, Any, Callable

import logging
import inspect

import model.events as events
import model.visual as visual

log = logging.getLogger("dimsum")


class Subscription:
    def __init__(
        self, manager: "SubscriptionManager", path_key: str, handler_fn: Callable
    ):
        super().__init__()
        self.manager = manager
        self.path_key = path_key
        self.handler_fn = handler_fn

    async def write(self, item: visual.Renderable):
        await self.handler_fn(item)

    def remove(self):
        self.manager.remove(self)


class SubscriptionManager(visual.Comms):
    def __init__(self):
        super().__init__()
        self.by_key: Dict[str, List[Subscription]] = {}

    def subscribe(self, path_key: str, handler_fn: Callable) -> Subscription:
        subscription = Subscription(self, path_key, handler_fn)
        self.by_key.setdefault(path_key, []).append(subscription)
        log.info("subscribed: %s", path_key)
        return subscription

    def remove(self, subscription: Subscription) -> bool:
        assert subscription.path_key in self.by_key
        for_key = self.by_key[subscription.path_key]
        if subscription in for_key:
            for_key.remove(subscription)
            log.info("unsubscribed: %s", subscription.path_key)
            return True
        else:
            return False

    async def somebody(self, key: str, r: visual.Renderable) -> bool:
        if key in self.by_key:
            # TODO Parallel
            for subscription in self.by_key[key]:
                await subscription.write(r)
            return True
        return False

    async def everybody(self, r: visual.Renderable) -> bool:
        # TODO Parallel
        for key, other in self.by_key.items():
            await other.write(r)
        return True


class EventBus:
    def __init__(self, handlers=None):
        super().__init__()
        self.handlers = {}
        self.modules = [f(self) for f in handlers] if handlers else []

    async def publish(self, event: events.Event, **kwargs):
        assert event
        log.info("publish:%s", event)
        await self.invoke_handlers(event)

    async def invoke_handler_type(self, klass, event: Union[Any]):
        if klass in self.handlers:
            handlers = self.handlers[klass]
            for fn in handlers:
                await fn(event=event, **event.kwargs)

    async def invoke_handlers(self, event: Union[Any]):
        for t in inspect.getmro(type(event)):
            await self.invoke_handler_type(t, event)

    def handler(self, klass):
        def final_decorator(func, **kwargs):
            log.info("add handler for %s (%s)", klass, func)
            if klass not in self.handlers:
                self.handlers[klass] = []
            self.handlers[klass].append(func)

        return final_decorator
