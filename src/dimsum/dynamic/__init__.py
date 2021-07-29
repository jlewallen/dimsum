from typing import List, Dict, Any

from model import Entity

from .core import Dynsum, LibraryBehavior, Cron, CronKey, CronEvent
from .calls import DynamicCallsListener, LogDynamicCalls, DynamicCall
from .behavior import Behavior

import scopes.behavior as behavior


def log_behavior(entity: Entity, entry: Dict[str, Any], executable=True):
    assert entity
    with entity.make(behavior.Behaviors) as behave:
        # If there's no default behavior then we're here because of
        # inherited behavior.
        b = behave.get_or_create_default()
        assert b
        b.executable = executable
        b.append(entry)
        entity.touch()


__all__: List[str] = [
    "Dynsum",
    "LibraryBehavior",
    "Cron",
    "CronKey",
    "CronEvent",
    "DynamicCallsListener",
    "LogDynamicCalls",
    "DynamicCall",  # TODO remove?
    "log_behavior",  # TODO remove
    "Behavior",
]
