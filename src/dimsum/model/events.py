import logging
import dataclasses
from typing import Any, Dict, List, Optional, Type

from .visual import Renderable
from .entity import Entity  # type only
from .inflection import infl

log = logging.getLogger("dimsum.model")

_all_events: List[Type["Event"]] = []


def event(klass: Type["Event"]):
    global _all_events
    _all_events.append(klass)
    log.debug("event: %s", klass)
    return klass


def get_all_events() -> List[Type["Event"]]:
    global _all_events
    return _all_events


class Event:
    @property
    def name(self) -> str:
        return self.__class__.__name__


@event
@dataclasses.dataclass
class TickEvent(Event):
    time: float


@event
@dataclasses.dataclass(frozen=True)
class StandardEvent(Event, Renderable):
    source: Entity
    area: Entity
    heard: Optional[List[Entity]]

    def render_entities(self, entities: List[Entity]) -> str:
        return infl.join([e.props.described for e in entities])
