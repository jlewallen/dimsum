import dataclasses
from typing import Any, Callable, Dict, List, Optional, Sequence, Union, Tuple
from datetime import datetime
from croniter import croniter

from loggers import get_logger
from model import Event

log = get_logger("dimsum.scheduling")


@dataclasses.dataclass(frozen=True)
class CronKey:
    entity_key: str
    spec: str


@dataclasses.dataclass(frozen=True)
class CronEvent(Event):
    entity_key: str
    spec: str


@dataclasses.dataclass(frozen=True)
class FutureTask:
    when: datetime


@dataclasses.dataclass(frozen=True)
class WhenCron(FutureTask):
    crons: List[CronKey]


@dataclasses.dataclass(frozen=True)
class QueuedTask(FutureTask):
    entity_key: str
    message: str


@dataclasses.dataclass
class CronTab:
    crons: List[CronKey]

    def get_future_task(self) -> Optional[WhenCron]:
        wc: Optional[WhenCron] = None
        base = datetime.now()
        log.debug("summarize: %s", base)
        curr: Optional[Tuple[datetime, List[CronKey]]] = None
        for cron in self.crons:
            iter = croniter(cron.spec, base)
            when = iter.get_next(datetime)
            if curr is None or when < curr[0]:
                curr = (when, [])
            if when == curr[0]:
                curr[1].append(cron)
            log.debug("%s iter=%s curr=%s", cron, when, curr)
        if curr:
            return WhenCron(curr[0], curr[1])
        return None
