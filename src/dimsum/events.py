from typing import Any
import logging


class Event:
    def __init__(self, **kwargs):
        super().__init__()
        self.kwargs = kwargs
        self.log = logging.getLogger("dimsum")

    async def accept(self, visitor: Any):
        if not hasattr(visitor, self.name):
            self.log.warning("handler-missing: %s", self.name)
            return None

        fn = getattr(visitor, self.name)
        self.log.debug("handler-invoke: %s", self.name)
        return await fn(**self.kwargs)

    @property
    def name(self):
        return self.__class__.__name__

    def __str__(self):
        return "%s<%s>" % (self.name, self.kwargs)

    def __repr__(self):
        return str(self)


class PlayerJoined(Event):
    pass


class ItemHeld(Event):
    pass


class ItemsMade(Event):
    pass


class ItemsDropped(Event):
    pass


class ItemObliterated(Event):
    pass
