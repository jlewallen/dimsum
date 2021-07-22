from typing import Dict, List, Optional, Sequence, Type, Any

from loggers import get_logger

from .entity import Entity, Scope, RootEntityClass, find_entity_area
from .context import MaterializeAndCreate


class WellKnown(Scope):
    def __init__(self, entities: Optional[Dict[str, str]] = None, **kwargs):
        super().__init__(**kwargs)
        self.entities = entities if entities else {}

    def get(self, local_key: str) -> Optional[str]:
        return self.entities[local_key] if local_key in self.entities else None

    def set(self, local_key: str, key: str):
        if self.get(local_key) == key:
            return False
        self.entities[local_key] = key
        return True


def get_well_known_key(entity: Entity, local_key: str) -> Optional[str]:
    with entity.make_and_discard(WellKnown) as wk:
        return wk.get(local_key)


def set_well_known_key(entity: Entity, local_key: str, key: str):
    with entity.make(WellKnown) as wk:
        if wk.set(local_key, key):
            entity.touch()
        else:
            wk.discard()


async def materialize_well_known_entity(
    origin: Entity,
    ctx: MaterializeAndCreate,
    local_key: str,
    create_args: Optional[Dict[str, Any]] = None,
) -> Entity:
    entity_key = get_well_known_key(origin, local_key)
    if entity_key:
        loaded = await ctx.try_materialize_key(entity_key)
        if loaded:
            return loaded
    if not create_args:
        raise Exception()
    entity = ctx.create_item(creator=origin, **create_args)
    set_well_known_key(origin, local_key, entity.key)
    return entity
