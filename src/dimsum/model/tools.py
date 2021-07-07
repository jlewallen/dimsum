import sys
import dataclasses
import enum
import logging
import traceback
import time

from typing import Any, Dict, List, Optional, Sequence

from model.entity import Entity
import model.scopes.apparel as apparel
import model.scopes.carryable as carryable
import model.scopes.mechanics as mechanics
import model.scopes.occupyable as occupyable
import model.scopes.behavior as behavior


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


def get_contributing_entities(world: Entity, player: Entity) -> EntitySet:
    entities = EntitySet()
    entities.add(Relation.WORLD, world)
    entities.add(Relation.SELF, player)
    area = area_of(player)
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


def area_of(entity: Entity) -> Optional[Entity]:
    if entity.has(occupyable.Occupyable):
        log.info("finding area for %s (self)", entity)
        return entity

    log.info("finding area for %s", entity)
    with entity.make_and_discard(occupyable.Occupying) as occupying:
        if occupying.area:
            log.debug("finding area for %s (occupying)", entity)
            return occupying.area

    with entity.make_and_discard(carryable.Location) as location:
        if location.container:
            log.debug("finding area for %s (container)", entity)
            return location.container

    return None


def log_behavior(entity: Entity, entry: Dict[str, Any]):
    assert entity
    log.info("logging '%s' behavior", entity)
    with entity.make(behavior.Behaviors) as behave:
        b = behave.get_default()
        assert b
        b.append(entry)
        entity.touch()


def log_behavior_exception(entity: Entity):
    assert entity
    ex_type, ex_value, tb = sys.exc_info()
    log_behavior(
        entity,
        dict(
            time=time.time(),
            exception=ex_type,
            value=ex_value,
            traceback=traceback.format_exc(),
        ),
    )


def flatten(l):
    return [item for sl in l for item in sl]
