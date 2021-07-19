import dataclasses
import logging
import time
import functools
import bisect
import json
import jsonpickle
from typing import List, Dict, Optional, Any

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

log = logging.getLogger("dimsum.scopes")


class PostMessage(Event):
    pass


@dataclasses.dataclass
@functools.total_ordering
class QueuedMessage:
    entity_key: str
    when: float
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


@dataclasses.dataclass
class DequeuedMessage:
    entity_key: str
    message: Any


class Post(Scope):
    def __init__(self, queue: Optional[List[QueuedMessage]] = None, **kwargs):
        super().__init__(**kwargs)
        self.queue: List[QueuedMessage] = queue if queue else []

    def enqueue(self, entity_key: str, when: float, message: str):
        qm = QueuedMessage(entity_key, when, message)
        bisect.insort(self.queue, qm)
        self.parent.touch()

    def dequeue(self, now: float) -> List[QueuedMessage]:
        if len(self.queue) == 0:
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


@dataclasses.dataclass
class PostService:
    entity: Entity

    async def future(self, receiver: Entity, when: float, message: PostMessage):
        with self.entity.make(Post) as post:
            serialized_message = serializing.serialize(message)
            post.enqueue(receiver.key, when, serialized_message)

    async def service(self, now: float) -> List[DequeuedMessage]:
        with self.entity.make(Post) as post:
            return [
                DequeuedMessage(qm.entity_key, jsonpickle.decode(qm.message))
                for qm in post.dequeue(now)
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
