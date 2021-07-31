import dataclasses
import time
import logging
from loggers import get_logger

from model import (
    Entity,
    Scope,
    Event,
    StandardEvent,
    Common,
    Success,
    Failure,
    get_all_events,
)
import tools


def _get_default_globals():
    import scopes.behavior as behavior
    import scopes.carryable as carryable
    import scopes.movement as movement
    import scopes.inbox as inbox
    import typing as imported_typing

    log = get_logger("dimsum.dynamic.user")
    log.setLevel(logging.INFO)  # affects tests, careful
    handler = logging.handlers.MemoryHandler(1024, target=logging.NullHandler())
    log.addHandler(handler)

    # TODO Can we pass an exploded module here?
    event_classes = {k.__name__: k for k in get_all_events()}
    return dict(
        log=log,
        dataclass=dataclasses.dataclass,
        tools=tools,
        Common=Common,
        Entity=Entity,
        Event=Event,
        Scope=Scope,
        Carryable=carryable.Carryable,
        Containing=carryable.Containing,
        Exit=movement.Exit,
        fail=Failure,
        ok=Success,
        time=time.time,
        t=imported_typing,
        log_handler=handler,  # private
        **event_classes,
    )
