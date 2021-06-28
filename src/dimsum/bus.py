from typing import Union, Any

import logging
import inspect
import model.events as events

log = logging.getLogger("dimsum")


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
