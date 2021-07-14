import logging
from typing import Dict, List, Optional, Sequence, Type, Any

from .properties import Common
from .entity import (
    Entity,
    Scope,
    RootEntityClass,
    find_entity_area,
    default_permissions_for,
)
from .context import Ctx

WorldKey = "world"
WelcomeAreaKey = "welcomeArea"
log = logging.getLogger("dimsum.model")


class Identifiers(Scope):
    def __init__(self, gid: int = 0, **kwargs):
        super().__init__(**kwargs)
        self.gid = gid
        self.acls = default_permissions_for(self.ourselves, name="ids")


def get_current_gid(entity: Entity) -> int:
    with entity.make(Identifiers) as ids:
        return ids.gid


def set_current_gid(entity: Entity, gid: int):
    with entity.make(Identifiers) as ids:
        if ids.gid != gid:
            ids.gid = gid
            log.info("gid-updated: %d", gid)
            entity.touch()


class World(Entity):
    def __init__(self, key=None, klass=None, props=None, **kwargs):
        super().__init__(
            key=WorldKey,
            klass=RootEntityClass,
            props=props if props else Common("World", desc="Ya know, everything"),
            **kwargs
        )

    # TODO Removing these causes a very strange modified during
    # iteration dict error. Would be worth seeing why!
    def __str__(self):
        return "$world"

    def __repr__(self):
        return "$world"
