import ast
import functools
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

from loggers import get_logger
from model import Entity, Scope, Map, Acls

DefaultKey = "b:default"
log = get_logger("dimsum.scopes")


@dataclass
class Behavior:
    acls: Acls = field(default_factory=functools.partial(Acls))
    python: Optional[str] = None
    executable: bool = True
    logs: List[Dict[str, Any]] = field(default_factory=list)

    # TODO remove eventually
    def __post_init__(self):
        if not hasattr(self, "logs"):
            self.logs = []

    def append(self, entry: Dict[str, Any]):
        self.logs.append(entry)
        self.logs = self.logs[-20:]

    def __hash__(self):
        return hash(self.python)


class BehaviorMap(Map):
    def get_all(self, behavior: str):
        pattern = "b:(.+):%s" % (behavior,)
        return [self.map[key] for key in self.keys_matching(pattern)]

    def get(self, key: str) -> Optional[Behavior]:
        return self.map[key] if key in self.map else None  # type:ignore

    def add(self, name, **kwargs):
        b = self.map[name] = Behavior(**kwargs)  # type:ignore
        return b

    def items(self):
        return self.map.items()


@dataclass
class BehaviorMeta:
    pass


@dataclass
class BehaviorCollection(Scope):
    entities: Dict[str, List[BehaviorMeta]] = field(default_factory=dict)


@dataclass
class Behaviors(Scope):
    behaviors: BehaviorMap = field(default_factory=BehaviorMap)

    def get_default(self) -> Optional[Behavior]:
        return self.behaviors.get(DefaultKey)

    def get_or_create_default(self) -> Behavior:
        if DefaultKey in self.behaviors:
            b = self.behaviors.get(DefaultKey)
            assert b
            return b
        self.ourselves.touch()
        return self.behaviors.add(DefaultKey)

    def add_behavior(self, world: Entity, **kwargs):
        # TODO This should be smarter. Only necessary for tick
        # receivers currently. Maye we just make tick special and run
        # over everything? This has elegance.
        if world:
            with world.make(BehaviorCollection) as world_behaviors:
                key = self.ourselves.key
                per_entity = world_behaviors.entities.setdefault(key, [])
                if len(per_entity) == 0:
                    per_entity.append(BehaviorMeta())
                    world.touch()
        self.ourselves.touch()
        return self.behaviors.add(DefaultKey, **kwargs)
