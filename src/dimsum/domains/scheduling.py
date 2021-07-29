import dataclasses
from typing import Any, Callable, Dict, List, Optional, Sequence, Union, Tuple
from datetime import datetime
from croniter import croniter

from loggers import get_logger
from dynamic import CronKey, Cron  # TODO move these and scheduling away?

log = get_logger("dimsum.domains")


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
    crons: List[Cron]

    def get_future_task(self) -> Optional[WhenCron]:
        wc: Optional[WhenCron] = None
        base = datetime.now()
        log.debug("summarize: %s", base)
        curr: Optional[Tuple[datetime, List[Cron]]] = None
        for cron in self.crons:
            iter = croniter(cron.spec, base)
            when = iter.get_next(datetime)
            if curr is None or when < curr[0]:
                curr = (when, [])
            if when == curr[0]:
                curr[1].append(cron)
            log.debug("%s iter=%s curr=%s", cron, when, curr)
        if curr:
            return WhenCron(curr[0], [c.key() for c in curr[1]])
        return None
