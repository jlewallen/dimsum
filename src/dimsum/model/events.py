from typing import Dict, List, Any, Optional

import logging
import enum
import dataclasses

import model.visual as visual

log = logging.getLogger("dimsum.model")


class Event:
    pass


@dataclasses.dataclass(frozen=True)
class StandardEvent(Event, visual.Renderable):
    living: Any
    area: Any
    heard: Optional[List[Any]]

    def render_string(self) -> Dict[str, str]:
        return {"standard": str(self)}
