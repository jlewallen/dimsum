import logging
from typing import Dict, List, Optional, Sequence, Type, Any

from .properties import Common
from .entity import Entity, Scope, RootEntityClass, find_entity_area
from .context import Ctx

WorldKey = "world"
log = logging.getLogger("dimsum.model")


class Identifiers(Scope):
    def __init__(self, gid: int = 0, **kwargs):
        super().__init__(**kwargs)
        self.gid = gid


class Welcoming(Scope):
    def __init__(self, area: Optional[Entity] = None, **kwargs):
        super().__init__(**kwargs)
        self.area = area


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


class World(Entity):
    def __init__(self, key=None, klass=None, props=None, **kwargs):
        super().__init__(
            key=WorldKey,
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

    def get_well_known(self, local_key: str) -> Optional[str]:
        with self.make_and_discard(WellKnown) as wk:
            return wk.get(local_key)

    def set_well_known(self, local_key: str, key: str):
        with self.make(WellKnown) as wk:
            if wk.set(local_key, key):
                self.touch()
            else:
                wk.discard()

    # TODO Removing these causes a very strange modified during
    # iteration dict error. Would be worth seeing why!
    def __str__(self):
        return "$world"

    def __repr__(self):
        return "$world"


async def materialize_well_known_entity(
    world: World, ctx: Ctx, local_key: str, create_args: Optional[Dict[str, Any]] = None
) -> Entity:
    entity_key = world.get_well_known(local_key)
    if entity_key:
        loaded = await ctx.try_materialize(key=entity_key)
        if loaded:
            return loaded
    create_args = create_args or {}
    entity = ctx.create_item(creator=world, **create_args)
    ctx.register(entity)
    world.set_well_known(local_key, entity.key)
    return entity
