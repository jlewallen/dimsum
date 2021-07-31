import sys
import traceback
import logging
import time
import contextvars
from typing import List, Dict, Optional, Any

from .core import DynamicEntitySources
from .calls import DynamicCall

active_behavior: contextvars.ContextVar = contextvars.ContextVar(
    "dimsum:behavior", default=None
)


def log_dynamic_call(
    sources: DynamicEntitySources,
    name: str,
    started: float,
    frame: Optional[Dict[str, Any]] = None,
    lokals: Optional[Dict[str, Any]] = None,
    fnargs: Optional[List[Any]] = None,
    fnkw: Optional[Dict[str, Any]] = None,
    exc_info: Optional[bool] = False,
    ex: Optional[Dict[str, Any]] = None,
):
    if exc_info:
        ex_type, ex_value, tb = sys.exc_info()
        ex = dict(
            exception=str(ex_type),
            value=str(ex_value),
            traceback=traceback.format_exc(),
        )

    assert sources.behaviors

    finished = time.time()
    logs = _get_buffered_logs(frame) if frame else []
    dc = DynamicCall(
        sources.entity_key,
        sources.behaviors[0].key,
        name,
        started,
        finished - started,
        context=dict(
            # frame=frame,
            # locals=lokals,
            # fnargs=serializing.serialize(fnargs),
            # fnkw=serializing.serialize(fnkw),
        ),
        logs=logs,
        exceptions=[ex] if ex else None,
    )
    db = active_behavior.get()
    assert db
    db._record(dc)


def _get_buffered_logs(frame: Dict[str, Any]) -> List[str]:
    def prepare(lr: logging.LogRecord) -> str:
        return lr.msg % lr.args

    if "log_handler" in frame:
        handler: logging.handlers.MemoryHandler = frame["log_handler"]
        records = [prepare(lr) for lr in handler.buffer]
        handler.flush()
        return records
    return []
