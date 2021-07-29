import dataclasses
import abc
from typing import List, Callable, Union, Tuple, Optional

from model import Entity, Event, Condition, Action, All, context
import grammars
import tools


@dataclasses.dataclass(frozen=True)
class CronKey:
    entity_key: str
    spec: str


@dataclasses.dataclass(frozen=True)
class Cron:
    entity_key: str
    spec: str
    handler: Callable = dataclasses.field(repr=False)

    def key(self) -> CronKey:
        return CronKey(self.entity_key, self.spec)


@dataclasses.dataclass(frozen=True)
class CronEvent(Event):
    entity_key: str
    spec: str


@dataclasses.dataclass(frozen=True)
class BehaviorSources:
    key: str
    source: str


@dataclasses.dataclass(frozen=True)
class DynamicEntitySources:
    entity_key: str
    behaviors: Tuple[BehaviorSources]


class LibraryBehavior:
    @abc.abstractmethod
    async def create(self, ds: "Dynsum"):
        raise NotImplementedError


class EntityBehavior(grammars.CommandEvaluator):
    @property
    def hooks(self):
        return All()  # empty hooks

    @property
    def crons(self) -> List[Cron]:
        return []

    async def notify(self, ev: Event, **kwargs):
        raise NotImplementedError


class NoopEntityBehavior(EntityBehavior):
    async def evaluate(self, command: str, **kwargs) -> Optional[Action]:
        return None

    async def notify(self, ev: Event, **kwargs):
        pass


class Dynsum:
    @abc.abstractmethod
    def language(self, prose: str, condition=None):
        raise NotImplementedError

    @abc.abstractmethod
    def cron(self, spec: str):
        raise NotImplementedError

    @abc.abstractmethod
    def received(self, hook: Union[type, str], condition=None):
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def hooks(self) -> All:
        return All()

    @abc.abstractmethod
    def behaviors(self, behaviors: List[LibraryBehavior]):
        raise NotImplementedError

    @abc.abstractmethod
    def evaluators(self, evaluators: List[grammars.CommandEvaluator]):
        raise NotImplementedError


class NoopDynsum(Dynsum):
    def language(self, prose: str, condition=None):
        pass

    def cron(self, spec: str):
        pass

    def received(self, hook: Union[type, str], condition=None):
        pass

    def behaviors(self, behaviors: List[LibraryBehavior]):
        pass

    def evaluators(self, evaluators: List[grammars.CommandEvaluator]):
        pass

    @property
    def hooks(self) -> All:
        return All()


@dataclasses.dataclass(frozen=True)
class LanguageHandler:
    prose: str
    condition: Condition
    fn: Callable = dataclasses.field(repr=False)


@dataclasses.dataclass(frozen=True)
class EventHandler:
    name: str
    condition: Condition
    fn: Callable = dataclasses.field(repr=False)
