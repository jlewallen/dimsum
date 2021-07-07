from typing import List, Sequence, Dict, Optional

import abc
import sys
import logging
import datetime
import time
import asyncio

import context

import model.properties as properties
import model.entity as entity

log = logging.getLogger("dimsum.scopes")


class Behavior:
    def __init__(self, python=None, logs=None, **kwargs):
        self.python = python
        self.logs = logs if logs else []

    def check(self):
        pass

    def error(self, messages: List[str], error):
        self.logs.extend(messages)

    def done(self, messages: List[str]):
        self.logs.extend(messages)
        self.logs = self.logs[-20:]


class ConditionalBehavior(Behavior):
    def __init__(self, **kwargs):
        super().__init__()

    @abc.abstractmethod
    def enabled(self, **kwargs) -> bool:
        raise NotImplementedError


class RegisteredBehavior:
    def __init__(self, name: str, behavior: ConditionalBehavior):
        super().__init__()
        self.name = name
        self.behavior = behavior


registered_behaviors: List[RegisteredBehavior] = []


def conditional(name):
    def wrap(klass):
        log.info("registered behavior: %s %s", name, klass)
        registered_behaviors.append(RegisteredBehavior(name, klass()))

    return wrap


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
        return self.behaviors.get("b:default")

    def add_behavior(self, world: entity.Entity, **kwargs):
        if world:
            with world.make(BehaviorCollection) as world_behaviors:
                world_behaviors.entities.append(self.ourselves)
        self.ourselves.touch()
        return self.behaviors.add("b:default", **kwargs)
