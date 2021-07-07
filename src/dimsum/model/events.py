from typing import Dict, List, Any, Optional

import logging
import enum
import dataclasses

import model.visual as visual

log = logging.getLogger("dimsum.model")


class Event:
    @property
    def name(self) -> str:
        return self.__class__.__name__


@dataclasses.dataclass
class HookEvent(Event):
    hook: str

    @property
    def name(self) -> str:
        return self.hook


@dataclasses.dataclass
class TickEvent(Event):
    time: float

    @property
    def name(self) -> str:
        return "tick"


@dataclasses.dataclass(frozen=True)
class StandardEvent(Event, visual.Renderable):
    living: Any
    area: Any
    heard: Optional[List[Any]]

    def render_string(self) -> Dict[str, str]:
        return {"standard": str(self)}
