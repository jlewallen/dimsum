import logging
from typing import Dict, List, Optional, Sequence, Type

from .properties import Common
from .entity import Entity, Scope, RootEntityClass, find_entity_area

Key = "world"
log = logging.getLogger("dimsum.model")


class Identifiers(Scope):
    def __init__(self, gid: int = 0, **kwargs):
        super().__init__(**kwargs)
        self.gid = gid


class Welcoming(Scope):
    def __init__(self, area: Optional[Entity] = None, **kwargs):
        super().__init__(**kwargs)
        self.area = area


class World(Entity):
    def __init__(self, key=None, klass=None, props=None, **kwargs):
        super().__init__(
            key=Key,
            klass=RootEntityClass,
            props=props if props else Common("World", desc="Ya know, everything"),
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

    def welcome_area(self) -> Entity:
        with self.make(Welcoming) as welcoming:
            return welcoming.area

    def change_welcome_area(self, area: Entity):
        with self.make(Welcoming) as welcoming:
            if welcoming.area != area:
                welcoming.area = area
                self.touch()

    async def apply_item_finder(
        self, person: Entity, finder, **kwargs
    ) -> Optional[Entity]:
        assert person
        assert finder
        area = await find_entity_area(person)
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
