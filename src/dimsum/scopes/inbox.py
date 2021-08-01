import time
import functools
import bisect
import heapq
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Union, Any

from loggers import get_logger
from model import (
    Entity,
    World,
    Common,
    Scope,
    Event,
    MaterializeAndCreate,
    materialize_well_known_entity,
)
import serializing
import scopes

log = get_logger("dimsum.scopes")


@dataclass
@functools.total_ordering
class QueuedMessage:
    when: datetime
    entity_key: str
    message: str

    def _is_valid_operand(self, other):
        return hasattr(other, "when")

    def __eq__(self, other):
        if not self._is_valid_operand(other):
            return NotImplemented
        return self.when == other.when

    def __lt__(self, other):
        if not self._is_valid_operand(other):
            return NotImplemented
        return self.when < other.when

    @staticmethod
    def create(when: datetime, entity_key: str, message: Event) -> "QueuedMessage":
        serialized_message = serializing.serialize(message)
        assert serialized_message
        return QueuedMessage(when, entity_key, serialized_message)


@dataclass(frozen=True)
class DequeuedMessage:
    when: datetime
    entity_key: str
    message: Any


@dataclass
class Post(Scope):
    queue: List[QueuedMessage] = field(default_factory=list)

    def enqueue(self, entity_key: str, when: Union[datetime, float], message: str):
        if isinstance(when, float):
            when = datetime.fromtimestamp(when)
        qm = QueuedMessage(when, entity_key, message)
        bisect.insort(self.queue, qm)
        self.parent.touch()

    def schedule(self, qm: QueuedMessage):
        if len(self.queue) == 0:
            bisect.insort(self.queue, qm)
            self.parent.touch()
            return True

        for item in self.queue:
            if item == qm:
                log.info("schedule(return): %s == %s", item, qm)
                return
            if item.when > qm.when:
                bisect.insort(self.queue, qm)
                self.parent.touch()
                return True

        return False

    def dequeue(self, now: datetime) -> List[QueuedMessage]:
        if len(self.queue) == 0:
            log.debug("dequeue empty")
            return []

        def _slice(i: int):
            removed = self.queue[:i]
            self.queue = self.queue[i + 1 :]
            self.parent.touch()
            log.info("dequeue removed=%s", removed)
            return removed

        for i, qm in enumerate(self.queue):
            if qm.when > now:
                if i == 0:
                    return []
                return _slice(i)

        return _slice(len(self.queue))


@dataclass
class PostService:
    entity: Entity

    async def future(self, when: datetime, receiver: Entity, message: Event):
        with self.entity.make(Post) as post:
            serialized_message = serializing.serialize(message)
            post.enqueue(receiver.key, when, serialized_message)

    async def schedule(self, qm: QueuedMessage):
        with self.entity.make(Post) as post:
            post.schedule(qm)

    async def service(self, when: datetime) -> List[DequeuedMessage]:
        with self.entity.make(Post) as post:
            return [
                DequeuedMessage(
                    qm.when,
                    qm.entity_key,
                    serializing.deserialize_non_entity(qm.message),
                )
                for qm in post.dequeue(when)
            ]

    async def peek(self, when: datetime) -> List[DequeuedMessage]:
        # We discard here so we can easily just use dequeue and ignore the side effects.
        with self.entity.make_and_discard(Post) as post:
            return [
                DequeuedMessage(
                    qm.when,
                    qm.entity_key,
                    serializing.deserialize_non_entity(qm.message),
                )
                for qm in post.dequeue(when)
            ]


PostServiceKey = "postService"


async def create_post_service(ctx: MaterializeAndCreate, world: World) -> PostService:
    post_service_entity = await materialize_well_known_entity(
        world,
        ctx,
        PostServiceKey,
        create_args=dict(props=Common("PostService"), klass=scopes.ServiceClass),
    )
    return PostService(post_service_entity)
