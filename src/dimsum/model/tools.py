from typing import List, Optional, Dict, Sequence

import dataclasses
import logging
import enum

from model.world import World
from model.entity import Entity

import model.game as game

import model.scopes.carryable as carryable
import model.scopes.apparel as apparel
import model.scopes.occupyable as occupyable
import model.scopes.mechanics as mechanics


log = logging.getLogger("dimsum.tools")


class Relation(enum.Enum):
    WORLD = "world"
    SELF = "self"
    HOLDING = "holding"
    WEARING = "wearing"
    GROUND = "ground"
    AREA = "area"
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
    entities.add(Relation.WORLD, world)
    entities.add(Relation.SELF, player)
    area = world.find_entity_area(player)
    if area:
        with area.make_and_discard(carryable.Containing) as ground:
            entities.add_all(Relation.GROUND, ground.holding)
        entities.add(Relation.AREA, area)
    with player.make_and_discard(carryable.Containing) as pockets:
        entities.add_all(Relation.HOLDING, pockets.holding)
    with player.make_and_discard(apparel.Apparel) as clothes:
        entities.add_all(Relation.WEARING, clothes.wearing)
    return entities


def is_holding(container: Entity, e: Entity) -> bool:
    with container.make_and_discard(carryable.Containing) as contains:
        return e in contains.holding


def default_heard_for(area: Optional[Entity] = None) -> List[Entity]:
    if area:
        with area.make_and_discard(occupyable.Occupyable) as here:
            return here.occupied
    return []


def hide(e: Entity):
    with e.make(mechanics.Visibility) as vis:
        vis.make_invisible()


def show(e: Entity):
    with e.make(mechanics.Visibility) as vis:
        vis.make_visible()


def hold(c: Entity, e: Entity):
    with c.make(carryable.Containing) as contains:
        contains.hold(e)


def area_of(c: Entity) -> Entity:
    with c.make_and_discard(carryable.Location) as location:
        if location.container:
            return location.container
    with c.make_and_discard(occupyable.Occupying) as occupying:
        if occupying.area:
            return occupying.area
    raise Exception()


def flatten(l):
    return [item for sl in l for item in sl]
