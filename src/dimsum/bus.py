from typing import Union, Any
import logging

log = logging.getLogger("dimsum")


class EventBus:
    def __init__(self, handlers=None):
        super().__init__()
        self.handlers = {}
        self.modules = [f(self) for f in handlers] if handlers else []

    async def publish(self, event: Union[Any]):
        raise NotImplementedError

    def invoke_handlers(self, event: Union[Any]):
        if type(event) in self.handlers:
            handlers = self.handlers[type(event)]
            for fn in handlers:
                fn(**event.kwargs)

    def handler(self, klass):
        def final_decorator(func, **kwargs):
            log.info("add handler for %s (%s)", klass, func)
            if klass not in self.handlers:
                self.handlers[klass] = []
            self.handlers[klass].append(func)

        return final_decorator
