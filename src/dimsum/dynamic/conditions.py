import dataclasses
import functools
from typing import List, Callable, Union, Tuple, Optional

from model import Entity, Event, Condition, Action, context
import tools


@dataclasses.dataclass
class Held(Condition):
    entity_key: str

    def applies(self) -> bool:
        entity = context.get().find_by_key(self.entity_key)
        assert entity
        return tools.in_pockets(entity)


@dataclasses.dataclass
class Ground(Condition):
    entity_key: str

    def applies(self) -> bool:
        entity = context.get().find_by_key(self.entity_key)
        assert entity
        return tools.on_ground(entity)


def bind_conditions(entity_key: str):
    return dict(
        Held=functools.partial(Held, entity_key),
        Ground=functools.partial(Ground, entity_key),
    )
