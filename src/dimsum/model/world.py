from typing import Any, Optional, Dict, List, Sequence, cast, Type
import time
import logging
import inflect

import bus
import context

import model.entity as entity
import model.game as game
import model.properties as properties

import model.scopes.behavior as behavior
import model.scopes.occupyable as occupyable
import model.scopes.carryable as carryable
import model.scopes.movement as movement
import model.scopes as scopes

DefaultMoveVerb = "walk"
TickHook = "tick"
WindHook = "wind"
Key = "world"
log = logging.getLogger("dimsum.model")
p = inflect.engine()


class EntityHooks(entity.Hooks):
    def describe(self, entity: entity.Entity) -> str:
        with entity.make_and_discard(carryable.Carryable) as carry:
            if carry.quantity > 1:
                return "{0} {1} (#{2})".format(
                    carry.quantity,
                    p.plural(entity.props.name, carry.quantity),
                    entity.props.gid,
                )
        return "{0} (#{1})".format(p.a(entity.props.name), entity.props.gid)


entity.hooks(EntityHooks())


class Welcoming(entity.Scope):
    def __init__(self, area: entity.Entity = None, **kwargs):
        super().__init__(**kwargs)
        self.area = area


class Remembering(entity.Scope):
    def __init__(self, entities: List[entity.Entity] = None, **kwargs):
        super().__init__(**kwargs)
        self.entities = entities if entities else []


class World(entity.Entity):
    def __init__(self, key=None, klass=None, props=None, **kwargs):
        super().__init__(
            key=Key,
            klass=entity.RootEntityClass,
            props=props
            if props
            else properties.Common("World", desc="Ya know, everything"),
            scopes=scopes.World,
            **kwargs
        )

    def welcome_area(self) -> entity.Entity:
        with self.make(Welcoming) as welcoming:
            return welcoming.area

    def change_welcome_area(self, area: entity.Entity):
        with self.make(Welcoming) as welcoming:
            welcoming.area = area

    def remember(self, e: entity.Entity):
        with self.make(Remembering) as remembering:
            remembering.entities.append(e)

    def find_entity_area(self, entity: entity.Entity) -> Optional[entity.Entity]:
        log.info("finding area for %s", entity)
        if entity.has(occupyable.Occupyable):
            return entity
        with entity.make_and_discard(occupyable.Occupying) as occupying:
            if occupying.area:
                return occupying.area
        with entity.make_and_discard(carryable.Location) as location:
            if location.container:
                return location.container
        return None

    def find_player_area(self, player: entity.Entity) -> entity.Entity:
        area = self.find_entity_area(player)
        assert area
        return area

    def apply_item_finder(
        self, person: entity.Entity, finder, **kwargs
    ) -> Optional[entity.Entity]:
        assert person
        assert finder
        area = self.find_player_area(person)
        log.info("applying finder:%s %s", finder, kwargs)
        found = finder.find_item(area=area, person=person, world=self, **kwargs)
        if found:
            log.info("found: {0}".format(found))
        else:
            log.info("found: nada")
        return found

    # NOTE Removing these causes a very strange modified during
    # iteration dict error. Would be worth seeing why!
    def __str__(self):
        return "$world"

    def __repr__(self):
        return "$world"
