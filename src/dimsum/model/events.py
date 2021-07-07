import dataclasses
import logging
from typing import Any, Dict, List, Optional, Type

import model.visual as visual

log = logging.getLogger("dimsum.model")


class Event:
    @property
    def name(self) -> str:
        return self.__class__.__name__


_all_events: List[Type[Event]] = []


def event(klass):
    global _all_events
    _all_events.append(klass)
    log.debug("event: %s", klass)
    return klass


def get_all():
    global _all_events
    return _all_events


@event
@dataclasses.dataclass
class TickEvent(Event):
    time: float


@event
@dataclasses.dataclass(frozen=True)
class StandardEvent(Event, visual.Renderable):
    living: Any
    area: Any
    heard: Optional[List[Any]]

    def render_string(self) -> Dict[str, str]:
        return {"standard": str(self)}
