import dataclasses
from typing import Any, Dict, List, Sequence

from loggers import get_logger

from .hooks import *
from .entity import *
from .game import *
from .visual import *

import scopes.mechanics as mechanics  # TODO bleh

log = get_logger("dimsum.model")


@dataclasses.dataclass
class ObservedEntity(Renderable):
    entity: Entity

    def render_tree(self) -> Dict[str, Any]:
        return {"entity": self.entity}


@all.observed.target()
async def observe_entity(entity: Entity) -> Sequence[ObservedEntity]:
    return [ObservedEntity(entity)]


class Observation(Reply, Renderable):
    pass


class Activity:
    pass


class HoldingActivity(Activity, Renderable):
    def __init__(self, entity: Entity):
        super().__init__()
        self.entity = entity

    def render_tree(self) -> Dict[str, Any]:
        return {"holding": self.entity}
