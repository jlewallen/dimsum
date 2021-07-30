import dataclasses
import functools
from typing import Any, Callable, Dict, List, Optional, Sequence, Union, Tuple
from datetime import datetime
from croniter import croniter

from loggers import get_logger
from model import Entity, World, Ctx, Event, MissingEntityException, CronKey, CronEvent
from domains import Session

import scopes.behavior as behavior
import scopes.inbox as inbox

log = get_logger("dimsum.scheduling")


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


@dataclasses.dataclass
class Scheduler:
    session: Session
    scheduled: Optional[FutureTask] = None
    _post_service_cached: Optional[inbox.PostService] = None

    async def service(self, now: datetime) -> Optional[datetime]:
        assert self.session.world

        log.info("scheduler: service %s", now)

        post_service = await self._post_service()
        queued = await post_service.service(now)
        for qm in queued:
            try:
                await self.session._notify_entity(
                    qm.entity_key, qm.message
                )  # TOD ugly private call
            except MissingEntityException as e:
                log.exception("missing entity", exc_info=True)

        # Refresh crons, scheduling any that may have been changed.
        # TODO Only do this per entity when modified.
        await self._refresh_crons(post_service)

        peeked = await post_service.peek(datetime.max)

        log.debug("scheduler: serviced waiting=%s", peeked)

        if peeked:
            return peeked[0].when

        return None

    async def peek(self, now: datetime) -> List[FutureTask]:
        assert self.session.world

        log.info("scheduler: peek %s", now)

        post_service = await self._post_service()
        return await post_service.peek(now)

    async def _refresh_crons(self, post_service: inbox.PostService):
        assert self.session.world

        log.info("crons: refreshing")

        removing: List[str] = []

        async def _get_crons(key: str):
            try:
                # Notice that refresh is intentionally False here
                # because False can easily blow away modifications.
                entity = await self.session.materialize(key=key)
                with entity.make(behavior.Behaviors) as behave:
                    if behave.get_default():
                        with self.session.ctx(entity=entity) as ctx:
                            crons = await ctx.find_crons()
                            assert crons is not None
                            return crons
            except MissingEntityException as e:
                log.exception("missing entity", exc_info=True)
                removing.append(key)
                return []

        with self.session.world.make(behavior.BehaviorCollection) as servicing:
            everything = servicing.entities.keys()
            crons = flatten([await _get_crons(key) for key in everything])

            tab = CronTab(crons)
            future_task = tab.get_future_task()
            if future_task:
                log.info("crons-scheduled: %s", future_task)
                post_service = await self._post_service()
                for cron in future_task.crons:
                    await post_service.schedule(
                        inbox.QueuedMessage.create(
                            future_task.when,
                            cron.entity_key,
                            CronEvent(cron.entity_key, cron.spec),
                        )
                    )

            for key in removing:
                log.warning("removing %s from world behaviors", key)
                del servicing.entities[key]
                self.session.world.touch()

        log.debug("crons: refreshed")

    async def _post_service(self):
        if self._post_service_cached:
            return self._post_service_cached
        # TODO could be session, though these a renarrow interfaces.
        assert self.session.world
        self._post_service_cached = await inbox.create_post_service(
            self.session, self.session.world
        )
        return self._post_service_cached


def flatten(l):
    return [item for sl in l for item in sl]
