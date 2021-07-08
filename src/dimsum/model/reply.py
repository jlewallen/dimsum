import dataclasses
import logging
from typing import Any, Dict, List, Sequence

import inflect
import model.entity as entity
import model.game as game
import model.visual as visual

import scopes.mechanics as mechanics

p = inflect.engine()
log = logging.getLogger("dimsum.model")


class Observation(game.Reply, visual.Renderable):
    def render_string(self) -> Dict[str, str]:
        return {"message": "some kind of observation"}


@dataclasses.dataclass
class ObservedEntity:
    entity: entity.Entity


class ObservedItem(ObservedEntity):
    def accept(self, visitor):
        return visitor.observed_entity(self)

    def __str__(self):
        return str(self.entity)

    def __repr__(self):
        return str(self)


class Activity:
    pass


class HoldingActivity(Activity):
    def __init__(self, item: entity.Entity):
        super().__init__()
        self.item = item

    def __str__(self):
        return "holding %s" % (self.item,)


class ObservedEntities:
    def __init__(self, entities: List[entity.Entity]):
        super().__init__()
        self.entities = entities

    def __str__(self):
        return str(p.join(self.entities))

    def __repr__(self):
        return str(self)


def observe(entity: Any) -> Sequence[ObservedEntity]:
    if entity.make(mechanics.Visibility).is_invisible:
        return []
    return [ObservedItem(entity)]


def flatten(l):
    return [item for sl in l for item in sl]
