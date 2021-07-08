import ast
import logging
from typing import Dict, List, Optional, Any

import model.entity as entity
import model.properties as properties

DefaultKey = "b:default"
log = logging.getLogger("dimsum.scopes")


class Behavior:
    def __init__(self, python=None, logs=None, **kwargs):
        self.python = python
        self.logs: List[Dict[str, Any]] = logs if logs else []

    def check(self):
        try:
            ast.parse(self.python)
            return True
        except:
            return False

    def append(self, entry: Dict[str, Any]):
        self.logs.append(entry)
        self.logs = self.logs[-20:]

    def __hash__(self):
        return hash(self.python)


class BehaviorMap(properties.Map):
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


class BehaviorCollection(entity.Scope):
    def __init__(self, entities=None, **kwargs):
        super().__init__(**kwargs)
        self.entities: List[entity.Entity] = entities if entities else []


class Behaviors(entity.Scope):
    def __init__(self, behaviors: Optional[BehaviorMap] = None, **kwargs):
        super().__init__(**kwargs)
        self.behaviors = behaviors if behaviors else BehaviorMap()

    def get_default(self) -> Optional[Behavior]:
        return self.behaviors.get(DefaultKey)

    def add_behavior(self, world: entity.Entity, **kwargs):
        # TODO This should be smarter. Only necessary for tick
        # receivers currently. Maye we just make tick special and run
        # over everything? This has elegance.
        if world:
            with world.make(BehaviorCollection) as world_behaviors:
                if self.ourselves not in world_behaviors.entities:
                    world_behaviors.entities.append(self.ourselves)
        self.ourselves.touch()
        return self.behaviors.add(DefaultKey, **kwargs)
