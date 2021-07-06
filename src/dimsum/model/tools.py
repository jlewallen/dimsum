from typing import List, Optional, Dict, Sequence

import dataclasses
import logging
import enum

from model.world import World
from model.entity import Entity

import model.game as game

import model.scopes.carryable as carryable
import model.scopes.occupyable as occupyable


class Relation(enum.Enum):
    HOLDING = "holding"
    GROUND = "ground"
    OTHER = "other"


@dataclasses.dataclass
class EntitySet:
    entities: Dict[Relation, List[Entity]] = dataclasses.field(default_factory=dict)

    def add(self, rel: Relation, e: Entity):
        self.entities.setdefault(rel, []).append(e)

    def add_all(self, rel: Relation, entities: Sequence[Entity]):
        for e in entities:
            self.add(rel, e)

    def get(self, rel: Relation) -> List[Entity]:
        return self.entities[rel]

    def all(self) -> Sequence[Entity]:
        return flatten([e for rel, e in self.entities.items()])


def get_contributing_entities(world: World, player: Entity) -> EntitySet:
    entities = EntitySet()
    entities.add(Relation.OTHER, world)
    entities.add(Relation.OTHER, player)
    area = world.find_entity_area(player)
    if area:
        with area.make_and_discard(carryable.Containing) as ground:
            entities.add_all(Relation.GROUND, ground.holding)
        entities.add(Relation.OTHER, area)
    with player.make_and_discard(carryable.Containing) as pockets:
        entities.add_all(Relation.HOLDING, pockets.holding)
    return entities


def is_holding(container: Entity, e: Entity) -> bool:
    with container.make_and_discard(carryable.Containing) as contains:
        return e in contains.holding


def default_heard_for(area: Optional[Entity] = None) -> List[Entity]:
    if area:
        with area.make_and_discard(occupyable.Occupyable) as here:
            return here.occupied
    return []


def flatten(l):
    return [item for sl in l for item in sl]
