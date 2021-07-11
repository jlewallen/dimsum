import ast
import logging
import dataclasses
import functools
from typing import Dict, List, Optional, Any

from model import Entity, Scope, Map, Acls

DefaultKey = "b:default"
log = logging.getLogger("dimsum.scopes")


@dataclasses.dataclass
class Behavior:
    acls: Acls = dataclasses.field(default_factory=functools.partial(Acls, "behavior"))
    python: Optional[str] = None
    executable: bool = True
    logs: List[Dict[str, Any]] = dataclasses.field(default_factory=list)

    def check(self):
        try:
            if self.python:
                ast.parse(self.python)
                return True
        except:
            pass
        return False

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
        b.check()
        return b

    def items(self):
        return self.map.items()

    def replace(self, map):
        typed = {key: Behavior(**value) for key, value in map.items()}
        for key, value in typed.items():
            value.check()
        return super().replace(**typed)


class BehaviorCollection(Scope):
    def __init__(self, entities=None, **kwargs):
        super().__init__(**kwargs)
        self.entities: List[Entity] = entities if entities else []


class Behaviors(Scope):
    def __init__(self, behaviors: Optional[BehaviorMap] = None, **kwargs):
        super().__init__(**kwargs)
        self.behaviors = behaviors if behaviors else BehaviorMap()

    def get_default(self) -> Optional[Behavior]:
        return self.behaviors.get(DefaultKey)

    def add_behavior(self, world: Entity, **kwargs):
        # TODO This should be smarter. Only necessary for tick
        # receivers currently. Maye we just make tick special and run
        # over everything? This has elegance.
        if world:
            with world.make(BehaviorCollection) as world_behaviors:
                if self.ourselves not in world_behaviors.entities:
                    world_behaviors.entities.append(self.ourselves)
        self.ourselves.touch()
        return self.behaviors.add(DefaultKey, **kwargs)
