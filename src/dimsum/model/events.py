from typing import Any

import logging
import enum

log = logging.getLogger("dimsum.model")


class Event:
    def __init__(self, **kwargs):
        super().__init__()
        self.kwargs = kwargs

    @property
    def name(self):
        return self.__class__.__name__

    def __str__(self):
        return "%s<%s>" % (self.name, self.kwargs)

    def __repr__(self):
        return str(self)


class Audience(enum.Enum):
    NONE = 1
    DIRECT = 2
    NEARBY = 3
    SURROUNDINGS = 4
    EVERYONE = 5


class StandardEvent(Event):
    @property
    def audience(self) -> Audience:
        return Audience.NEARBY


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
