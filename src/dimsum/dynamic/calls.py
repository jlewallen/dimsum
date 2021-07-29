import dataclasses
from typing import Any, Callable, Dict, List, Optional, Sequence, Union

from loggers import get_logger


@dataclasses.dataclass
class DynamicCall:
    entity_key: str
    behavior_key: str
    name: str
    time: float
    elapsed: float
    logs: List[str]
    exceptions: Optional[List[Dict[str, Any]]]
    context: Dict[str, Any] = dataclasses.field(repr=False, default_factory=dict)


class DynamicCallsListener:
    async def save_dynamic_calls_after_success(self, calls: List[DynamicCall]):
        raise NotImplementedError

    async def save_dynamic_calls_after_failure(self, calls: List[DynamicCall]):
        raise NotImplementedError


class LogDynamicCalls(DynamicCallsListener):
    @property
    def log(self):
        return get_logger("dimsum.dynamic.calls")

    def _log_calls(self, calls: List[DynamicCall]):
        for call in calls:
            self.log.info("calls: %s", call)

    async def save_dynamic_calls_after_success(self, calls: List[DynamicCall]):
        self._log_calls(calls)

    async def save_dynamic_calls_after_failure(self, calls: List[DynamicCall]):
        self._log_calls(calls)
