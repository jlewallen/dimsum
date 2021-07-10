import logging
import dataclasses
from typing import Any, Dict, List, Sequence

from .hooks import *
from .entity import *
from .game import *
from .visual import *
import scopes.mechanics as mechanics

log = logging.getLogger("dimsum.model")


class Observation(Reply, Renderable):
    def render_string(self) -> Dict[str, str]:
        return {"message": "some kind of observation"}


@dataclasses.dataclass
class ObservedEntity:
    entity: Entity


class Activity:
    pass


class HoldingActivity(Activity):
    def __init__(self, item: Entity):
        super().__init__()
        self.item = item


class ObservedEntities:
    def __init__(self, entities: List[Entity]):
        super().__init__()
        self.entities = entities


@all.observed.target
def observe(entity: Entity) -> Sequence[ObservedEntity]:
    return [ObservedEntity(entity)]
