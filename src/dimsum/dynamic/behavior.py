import dataclasses
import functools
import time
from typing import Any, Callable, Dict, List, Optional, Sequence, Union

from loggers import get_logger
from model import Entity, Event, ManagedHooks, CronKey
import scopes.behavior as behavior
import grammars
import tools

from .core import DynamicEntitySources, BehaviorSources, EntityBehavior
from .calls import DynamicCall, DynamicCallsListener
from .compilation import _compile
from .ldc import log_dynamic_call, active_behavior

log = get_logger("dimsum.dynamic")


@dataclasses.dataclass
class Behavior:
    listener: DynamicCallsListener
    entities: tools.EntitySet
    previous: Optional["Behavior"] = None
    calls: List[DynamicCall] = dataclasses.field(default_factory=list)

    def _get_behaviors(self, e: Entity, c: Entity) -> List[DynamicEntitySources]:
        inherited = self._get_behaviors(e, c.parent) if c.parent else []
        with c.make_and_discard(behavior.Behaviors) as behave:
            b = behave.get_default()

            ignoring = flatten([[b] if b and not b.executable else []])
            if len(ignoring):
                log.warning("unexecutable: %s", ignoring)

            return (
                [
                    DynamicEntitySources(
                        e.key, (BehaviorSources(behavior.DefaultKey, b.python),)
                    )
                ]
                if b and b.executable and b.python
                else []
            ) + inherited

    @functools.cached_property
    def _behaviors(self) -> Dict[Entity, List[DynamicEntitySources]]:
        return {e: self._get_behaviors(e, e) for e in self.entities.all()}

    def _compile_behavior(
        self, entity: Entity, sources: DynamicEntitySources
    ) -> EntityBehavior:
        started = time.time()
        try:
            return _compile(sources, compiled_name=f"behavior[{entity}]")
        except:
            log_dynamic_call(sources, ":compile:", started, exc_info=True)
            raise

    @functools.cached_property
    def _compiled(self) -> Sequence[EntityBehavior]:
        return flatten(
            [
                [self._compile_behavior(entity, sources) for sources in all_for_entity]
                for entity, all_for_entity in self._behaviors.items()
            ]
        )

    @property
    def dynamic_hooks(self) -> List["ManagedHooks"]:
        return [c.hooks for c in self._compiled]

    @property
    def evaluators(self) -> Sequence[grammars.CommandEvaluator]:
        return self._compiled

    @property
    def lazy_evaluator(self) -> grammars.CommandEvaluator:
        return grammars.LazyCommandEvaluator(lambda: self.evaluators)

    async def find_crons(self) -> List[CronKey]:
        return flatten([c.crons for c in self._compiled])

    async def notify(self, ev: Event, **kwargs):
        for target in [c for c in self._compiled]:
            await target.notify(ev, **kwargs)

    async def verify(self):
        log.info("evaluators: %s", self.evaluators)

    async def __aenter__(self):
        self.previous = active_behavior.get()
        active_behavior.set(self)
        return self

    async def __aexit__(self, type, value, traceback):
        if self.previous:
            for dc in self.calls:
                self.previous._record(dc)
        else:
            if type:
                log.info("exiting: '%s' %s listener=%s", type, value, self.listener)
                if not self.calls:
                    log.warning("dynamic calls empty (exception)")
            if self.calls:
                if type:
                    await self.listener.save_dynamic_calls_after_failure(self.calls)
                else:
                    await self.listener.save_dynamic_calls_after_success(self.calls)

        active_behavior.set(self.previous)
        return False

    def _record(self, dc: DynamicCall):
        self.calls.append(dc)


def flatten(l):
    return [item for sl in l for item in sl]
