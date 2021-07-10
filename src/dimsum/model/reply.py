import logging
import dataclasses
import inflect
from typing import Any, Dict, List, Sequence

from .hooks import *
from .entity import *
from .game import *
from .visual import *
import scopes.mechanics as mechanics

log = logging.getLogger("dimsum.model")
p = inflect.engine()


class Observation(Reply, Renderable):
    def render_string(self) -> Dict[str, str]:
        return {"message": "some kind of observation"}


@dataclasses.dataclass
class ObservedEntity:
    entity: Entity

    def __str__(self):
        return str(self.entity)

    def __repr__(self):
        return str(self)


class Activity:
    pass


class HoldingActivity(Activity):
    def __init__(self, item: Entity):
        super().__init__()
        self.item = item

    def __str__(self):
        return "holding %s" % (self.item,)


class ObservedEntities:
    def __init__(self, entities: List[Entity]):
        super().__init__()
        self.entities = entities

    def __str__(self):
        return str(p.join(self.entities))

    def __repr__(self):
        return str(self)


@all.observed.target
def observe(entity: Entity) -> Sequence[ObservedEntity]:
    return [ObservedEntity(entity)]
