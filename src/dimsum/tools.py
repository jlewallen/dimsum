import dataclasses
import enum
from typing import Dict, List, Optional, Sequence

from loggers import get_logger
from model import (
    Common,
    Entity,
    World,
    SecurityContext,
    SecurityMappings,
    context,
    MaterializeAndCreate,
    materialize_well_known_entity,
)
import scopes.apparel as apparel
import scopes.carryable as carryable
import scopes.mechanics as mechanics
import scopes.movement as movement
import scopes.occupyable as occupyable
import scopes.behavior as behavior
import scopes.users as users
import scopes.ownership as owning
import scopes


log = get_logger("dimsum.tools")


class Relation(enum.Enum):
    WORLD = "world"
    SELF = "self"
    HOLDING = "holding"
    WEARING = "wearing"
    GROUND = "ground"
    AREA = "area"
    OTHER = "other"

    def __repr__(self):
        return self.name


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


def get_holding(entity: Entity) -> List[Entity]:
    with entity.make_and_discard(carryable.Containing) as container:
        return container.holding


def is_holding(container: Entity, e: Entity) -> bool:
    with container.make_and_discard(carryable.Containing) as contains:
        return e in contains.holding


def in_pockets(e: Entity) -> bool:
    with e.make_and_discard(carryable.Location) as location:
        assert location.container
        if location.container.klass == scopes.LivingClass:
            return True
    return False


def on_ground(e: Entity) -> bool:
    with e.make_and_discard(carryable.Location) as location:
        assert location.container
        if location.container.klass == scopes.AreaClass:
            return True
    return False


def default_heard_for(
    area: Optional[Entity] = None, excepted: Optional[List[Entity]] = None
) -> List[Entity]:
    if area:
        with area.make_and_discard(occupyable.Occupyable) as here:
            if excepted:
                return [o for o in here.occupied if o not in excepted]
            return here.occupied
    return []


def hide(e: Entity):
    with e.make(mechanics.Visibility) as vis:
        vis.make_invisible()


def show(e: Entity):
    with e.make(mechanics.Visibility) as vis:
        vis.make_visible()


def set_presence(e: Entity, p: mechanics.Presence):
    with e.make(mechanics.Visibility) as vis:
        if vis.visible.presence != p:
            vis.visible.presence = p
            e.touch()


def presence(e: Entity, short=False, long=False):
    if short:
        set_presence(e, mechanics.Presence.InlineShort())
    elif long:
        set_presence(e, mechanics.Presence.InlineLong())


def is_presence(e: Entity, p: mechanics.Presence):
    with e.make(mechanics.Visibility) as vis:
        return vis.visible.presence == p


def is_presence_distinct(e: Entity) -> bool:
    return is_presence(e, mechanics.Presence.Distinct())


def is_presence_inline_short(e: Entity) -> bool:
    return is_presence(e, mechanics.Presence.InlineShort())


def is_presence_inline_long(e: Entity) -> bool:
    return is_presence(e, mechanics.Presence.InlineLong())


def hold(c: Entity, e: Entity):
    with c.make(carryable.Containing) as contains:
        held = contains.hold(e)
        context.get().register(held)


def area_of(entity: Entity) -> Optional[Entity]:
    if entity.has(occupyable.Occupyable):
        log.debug("finding area for %s (self)", entity)
        return entity

    log.debug("finding area for %s", entity)
    with entity.make_and_discard(occupyable.Occupying) as occupying:
        if occupying.area:
            log.debug("finding area for %s (occupying)", entity)
            return occupying.area

    with entity.make_and_discard(carryable.Location) as location:
        if location.container:
            log.debug("finding area for %s (container)", entity)
            return area_of(location.container)

    return None


def get_person_security_context(entity: Entity) -> SecurityContext:
    owner_key = owning.get_owner_key(entity)
    mappings: Dict[str, str] = {}
    with entity.make_and_discard(users.Groups) as groups:
        mappings.update({key: entity.key for key in groups.memberships})
    return SecurityContext(entity.key, mappings)


def get_entity_security_context(
    outer: SecurityContext, entity: Entity
) -> SecurityContext:
    owner_key = owning.get_owner_key(entity)
    mappings: Dict[str, str] = {SecurityMappings.Owner: owner_key}
    return SecurityContext(outer.identity, {**outer.mappings, **mappings})


def move(moving: Entity, destination: Entity):
    location = moving.make_and_discard(carryable.Location).container
    assert location
    try:
        with location.make(carryable.Containing) as from_container:
            with destination.make(carryable.Containing) as to_container:
                if from_container.contains(moving):
                    from_container.unhold(moving)
                to_container.hold(moving)
    except:
        log.error("failed to move %s to %s from %s", moving, destination, location)
        log.exception("exception", exc_info=True)
        raise


LimboKey = "limbo"


async def move_to_limbo(world: World, ctx: MaterializeAndCreate, moving: Entity):
    destination = await materialize_well_known_entity(
        world,
        ctx,
        LimboKey,
        create_args=dict(props=Common("Limbo"), klass=scopes.AreaClass),
    )
    move(moving, destination)


async def move_from_limbo(world: World, moving: Entity, destination: Entity):
    move(moving, destination)


def flatten(l):
    return [item for sl in l for item in sl]


def set_exit(
    exit: Entity, area: Optional[Entity] = None, unavailable: Optional[str] = None
) -> Entity:
    with exit.make(movement.Exit) as e:
        if unavailable:
            # TODO check for reason difference?
            e.unavailable = movement.Unavailable(reason=unavailable)
            exit.touch()
        elif e.unavailable:
            e.unavailable = None
            exit.touch()

        if area and area.key != e.area.key:
            e.area = area
            exit.touch()

        return e.area


class NoContainerException(Exception):
    pass


def container(entity: Entity) -> Entity:
    with entity.make_and_discard(carryable.Location) as location:
        if location.container:
            return location.container
    raise NoContainerException()


def orphan(entity: Entity):
    with entity.make(carryable.Location) as location:
        if location.container:
            with location.container.make(carryable.Containing) as container:
                assert container.unhold(entity)
            location.container = None
            entity.touch()
