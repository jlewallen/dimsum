from typing import Any


class Event:
    def __init__(self, **kwargs):
        super().__init__()
        self.kwargs = kwargs

    def accept(self, visitor: Any):
        n = self.__class__.__name__
        if hasattr(visitor, n):
            return getattr(visitor, n)(**self.kwargs)
        return None


class PlayerJoined(Event):
    pass


class ItemHeld(Event):
    pass


class ItemMade(Event):
    pass


class ItemsDropped(Event):
    pass


class ItemObliterated(Event):
    pass
