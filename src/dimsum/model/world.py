import dataclasses
from typing import Dict, List, Optional, Sequence, Type, Any

from loggers import get_logger

from .properties import Common
from .entity import (
    Entity,
    Scope,
    RootEntityClass,
)
from .permissions import Acls
from .context import Ctx

WorldKey = "world"
WelcomeAreaKey = "welcomeArea"
log = get_logger("dimsum.model")


@dataclasses.dataclass
class Identifiers(Scope):
    gid: int = 0
    acls: Acls = dataclasses.field(default_factory=Acls.everybody_writes)


def get_current_gid(entity: Entity) -> int:
    with entity.make(Identifiers) as ids:
        return ids.gid


def set_current_gid(entity: Entity, gid: int):
    with entity.make(Identifiers) as ids:
        if ids.gid < gid:
            log.info("gid-updated: %d (was %d)", gid, ids.gid)
            ids.gid = gid
            entity.touch()
        else:
            log.debug("gid-ignored: %d (was %d)", gid, ids.gid)


class World(Entity):
    def __init__(self, key=None, klass=None, props=None, **kwargs):
        super().__init__(
            key=WorldKey,
            klass=RootEntityClass,
            props=props if props else Common("World", desc="Ya know, everything"),
            **kwargs
        )
