import logging
from typing import Dict, List, Optional, Sequence, Type

import inflect
import model.entity as entity
import model.properties as properties
import model.scopes as scopes
import model.scopes.behavior as behavior
import model.scopes.carryable as carryable
import model.tools as tools

Key = "world"
log = logging.getLogger("dimsum.model")
p = inflect.engine()


class EntityHooks(entity.Hooks):
    def describe(self, entity: entity.Entity) -> str:
        if entity.klass == scopes.LivingClass:
            return "{0} (#{1})".format(entity.props.name, entity.props.gid)
        if entity.klass == scopes.AreaClass:
            return "{0} (#{1})".format(entity.props.name, entity.props.gid)
        if entity.has(carryable.Carryable):
            with entity.make_and_discard(carryable.Carryable) as carry:
                if carry.quantity > 1:
                    return "{0} {1} (#{2})".format(
                        carry.quantity,
                        p.plural(entity.props.name, carry.quantity),
                        entity.props.gid,
                    )
        return "{0} (#{1})".format(p.a(entity.props.name), entity.props.gid)

    def cleanup(self, entity: entity.Entity, world: Optional["World"] = None, **kwargs):
        assert world
        if world.has(behavior.BehaviorCollection):
            log.info("cleanup %s", entity)
            with world.make(behavior.BehaviorCollection) as collection:
                if entity in collection.entities:
                    collection.entities.remove(entity)
                    world.touch()


entity.hooks(EntityHooks())


class Identifiers(entity.Scope):
    def __init__(self, gid: int = 0, **kwargs):
        super().__init__(**kwargs)
        self.gid = gid


class Welcoming(entity.Scope):
    def __init__(self, area: Optional[entity.Entity] = None, **kwargs):
        super().__init__(**kwargs)
        self.area = area


class Remembering(entity.Scope):
    def __init__(self, entities: Optional[List[entity.Entity]] = None, **kwargs):
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

    def gid(self) -> int:
        with self.make(Identifiers) as ids:
            return ids.gid

    def update_gid(self, gid: int):
        with self.make(Identifiers) as ids:
            if ids.gid != gid:
                ids.gid = gid
                self.touch()

    def welcome_area(self) -> entity.Entity:
        with self.make(Welcoming) as welcoming:
            return welcoming.area

    def change_welcome_area(self, area: entity.Entity):
        with self.make(Welcoming) as welcoming:
            if welcoming.area != area:
                welcoming.area = area
                self.touch()

    def remember(self, e: entity.Entity):
        with self.make(Remembering) as remembering:
            remembering.entities.append(e)
            self.touch()

    def find_entity_area(self, entity: entity.Entity) -> Optional[entity.Entity]:
        return tools.area_of(entity)

    def find_person_area(self, person: entity.Entity) -> entity.Entity:
        area = self.find_entity_area(person)
        assert area
        return area

    async def apply_item_finder(
        self, person: entity.Entity, finder, **kwargs
    ) -> Optional[entity.Entity]:
        assert person
        assert finder
        area = self.find_person_area(person)
        log.info("applying finder:%s %s", finder, kwargs)
        found = await finder.find_item(area=area, person=person, world=self, **kwargs)
        if found:
            log.info("found: {0}".format(found))
        else:
            log.info("found: nada")
        return found

    # TODO Removing these causes a very strange modified during
    # iteration dict error. Would be worth seeing why!
    def __str__(self):
        return "$world"

    def __repr__(self):
        return "$world"
