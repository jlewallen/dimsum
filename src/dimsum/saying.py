import abc
import dataclasses
import json
import logging
from typing import Callable, Dict, List, Optional, Union, Any

import tools
from model import (
    Entity,
    event,
    Event,
    Reply,
    Success,
    Renderable,
    find_entity_area,
    context,
)

log = logging.getLogger("dimsum")


@event
@dataclasses.dataclass(frozen=True)
class DynamicMessage(Event, Renderable):
    source: Entity
    area: Entity
    heard: Optional[List[Entity]]
    message: Reply


class Notify:
    @abc.abstractmethod
    def applies(self, hook: str) -> bool:
        raise NotImplementedError

    @abc.abstractmethod
    async def invoke(self, handler: Callable, *args, **kwargs):
        raise NotImplementedError


@dataclasses.dataclass(frozen=True)
class NotifyAll(Notify):
    hook: str
    event: Event

    def applies(self, hook: str) -> bool:
        return self.hook == hook

    def invoke(self, handler, *args, **kwargs):
        return handler(*args, ev=self.event, **kwargs)


@dataclasses.dataclass
class Say:
    nearby_queue: List[Reply] = dataclasses.field(default_factory=list)
    player_queue: Dict[Entity, List[Reply]] = dataclasses.field(default_factory=dict)

    def nearby(self, message: Union[Reply, str]):
        if isinstance(message, str):
            r = Success(message)
        self.nearby_queue.append(r)

    def player(self, person: Entity, message: Union[Reply, str]):
        if isinstance(message, str):
            r = Success(message)
        self.player_queue.setdefault(person, []).append(r)

    async def _pub(self, **kwargs):
        await context.get().publish(DynamicMessage(**kwargs))

    async def publish(self, source: Entity):
        area = await find_entity_area(source)
        assert area

        for player, queue in self.player_queue.items():
            for e in queue:
                await self._pub(
                    source=source,
                    area=area,
                    heard=[player],
                    message=e,
                )

        self.player_queue = {}

        heard = tools.default_heard_for(area)
        for e in self.nearby_queue:
            await self._pub(
                source=source,
                area=area,
                heard=heard,
                message=e,
            )

        self.nearby_queue = []
