from typing import List, Union, Dict, Optional, Any

import abc
import logging
import dataclasses
import json

import context

import model.entity as entity
import model.game as game
import model.events as events
import model.tools as tools


@dataclasses.dataclass(frozen=True)
class DynamicMessage(events.StandardEvent):
    message: game.Reply

    def render_string(self) -> Dict[str, str]:
        return json.loads(json.dumps(self.message))  # TODO json fuckery


class Notify:
    @abc.abstractmethod
    def applies(self, hook: str) -> bool:
        raise NotImplementedError

    @abc.abstractmethod
    def invoke(self, *args, **kwargs):
        raise NotImplementedError


@dataclasses.dataclass(frozen=True)
class NotifyEntity(Notify):
    entity: entity.Entity
    hook: str
    kwargs: Dict[str, Any]

    def applies(self, hook: str) -> bool:
        return self.hook == hook

    def invoke(self, handler, *args, **kwargs):
        return handler(*args, self.entity, **kwargs)


@dataclasses.dataclass(frozen=True)
class NotifyAll(Notify):
    hook: str
    kwargs: Dict[str, Any]

    def applies(self, hook: str) -> bool:
        return self.hook == hook

    def invoke(self, handler, *args, **kwargs):
        return handler(*args, **kwargs)


@dataclasses.dataclass
class Say:
    notified: List[Notify] = dataclasses.field(default_factory=list)
    everyone_queue: List[game.Reply] = dataclasses.field(default_factory=list)
    nearby_queue: List[game.Reply] = dataclasses.field(default_factory=list)
    player_queue: List[game.Reply] = dataclasses.field(default_factory=list)

    def notify(self, entity: entity.Entity, message: str, **kwargs):
        self.notified.append(NotifyEntity(entity, message, kwargs))

    def everyone(self, message: Union[game.Reply, str]):
        if isinstance(message, str):
            r = game.Success(message)
        self.everyone_queue.append(r)

    def nearby(self, message: Union[game.Reply, str]):
        if isinstance(message, str):
            r = game.Success(message)
        self.player_queue.append(r)

    def player(self, message: Union[game.Reply, str]):
        if isinstance(message, str):
            r = game.Success(message)
        self.player_queue.append(r)

    async def _pub(self, **kwargs):
        await context.get().publish(DynamicMessage(**kwargs))

    async def publish(self, area: entity.Entity, player: entity.Entity):
        for e in self.player_queue:
            await self._pub(
                living=player,
                area=area,
                heard=[player],
                message=e,
            )

        heard = tools.default_heard_for(area)
        for e in self.nearby_queue:
            await self._pub(
                living=player,
                area=area,
                heard=heard,
                message=e,
            )
