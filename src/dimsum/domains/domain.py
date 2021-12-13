import dataclasses
from datetime import datetime
from typing import Any, Callable, Dict, List, Literal, Optional, Sequence, Union, Tuple

from loggers import get_logger
from model import Comms
from storage import EntityStorage, SqliteStorage
from bus import SubscriptionManager

import handlers
import dynamic

from .session import Session
from .ctx import WorldCtx

log = get_logger("dimsum.domains")


class Domain:
    def __init__(
        self,
        store: Optional[EntityStorage] = None,
        subscriptions: Optional[SubscriptionManager] = None,
        **kwargs,
    ):
        super().__init__()
        self.store = store if store else SqliteStorage(":memory:")
        self.subscriptions = subscriptions if subscriptions else SubscriptionManager()
        self.comms: Comms = self.subscriptions
        self.handlers = [handlers.create(self.subscriptions)]

    def session(self) -> Session:
        log.info("session:new")

        return Session(
            store=self.store,
            handlers=self.handlers,
            ctx_factory=self.create_ctx,
            calls_saver=self.create_calls_saver,
        )

    def create_ctx(self, **kwargs):
        return WorldCtx(**kwargs)

    def create_calls_saver(self, session: "Session"):
        return SaveDynamicCalls(self, session)

    async def reload(self):
        return Domain(empty=True, store=self.store)

    async def close(self):
        await self.store.close()


@dataclasses.dataclass
class SaveDynamicCalls(dynamic.DynamicCallsListener):
    domain: "Domain"
    session: "Session"

    @property
    def log(self):
        return get_logger("dimsum.dynamic.calls")

    async def _update_in_session(
        self, session: "Session", calls: List[dynamic.DynamicCall], executable
    ):
        for call in calls:
            entity = await session.materialize(key=call.entity_key)
            assert entity
            self.log.info("calls: %s key=%s", entity, entity.key)
            self.log.info("calls: %s %s", entity, call)
            dynamic.log_behavior(
                entity,
                dict(
                    context=call.context,
                    logs=call.logs,
                    exceptions=call.exceptions,
                    success=not call.exceptions,
                    time=call.time,
                    elapsed=call.elapsed,
                ),
                executable=executable,
            )

    async def save_dynamic_calls_after_success(self, calls: List[dynamic.DynamicCall]):
        self.log.info("success: saving calls using existing session")
        await self._update_in_session(self.session, calls, True)

    async def save_dynamic_calls_after_failure(self, calls: List[dynamic.DynamicCall]):
        self.log.info("failure: saving calls using pristine session")
        pristine = await self.domain.reload()
        with pristine.session() as session:
            await self._update_in_session(session, calls, False)
            await session.save()

        # Ensure no attempt is made.
        session.rollback()
