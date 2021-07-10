import abc
import logging
import dataclasses
import functools
import contextvars
import asyncio
from typing import List, Optional, Callable, Dict, Any
from weakref import ref, ReferenceType

from .conditions import Condition
from .context import get

log = logging.getLogger("dimsum.hooks")
live_hooks: contextvars.ContextVar = contextvars.ContextVar("dimsum:hooks")


@dataclasses.dataclass
class RegisteredHook:
    fn: Callable
    condition: Optional[Condition] = None


@dataclasses.dataclass
class Hook:
    manager: "ManagedHooks"
    name: str
    fn: Optional[Callable] = None
    hooks: List[RegisteredHook] = dataclasses.field(default_factory=lambda: [])

    def target(self, fn):
        log.info("hook:target: %s", fn)

        assert not self.fn
        self.fn = fn

        def wrap(*args, **kwargs):
            all_hooks = []
            extended = live_hooks.get(None)
            if extended:
                all_hooks += extended._get_extra_hooks(self.name)
            return self._invoke(
                self.name, self.fn, self.hooks + all_hooks, args, kwargs
            )

        return wrap

    @staticmethod
    def _invoke(name, call, hooks, args, kwargs):
        log.info("hook:call '%s' hooks=%s args=%s kwargs=%s", name, hooks, args, kwargs)

        for registered in hooks:
            if registered.condition:
                value = get().evaluate(registered.condition)
                if not value:
                    continue
            call = functools.partial(registered.fn, call)

        return call(*args, **kwargs)

    def hook(self, wrapped=None, condition: Optional[Condition] = None):
        if wrapped is None:
            return functools.partial(self.hook, condition=condition)

        self.hooks.append(RegisteredHook(wrapped, condition))

        def wrap(fn):
            return fn

        return wrap


@dataclasses.dataclass
class ManagedHooks:
    everything: Dict[str, Hook] = dataclasses.field(default_factory=dict, init=False)

    def create_hook(self, name: str) -> Hook:
        return self.everything.setdefault(name, Hook(self, name))

    def _get_hooks(self, name: str) -> List[RegisteredHook]:
        if name in self.everything:
            return self.everything[name].hooks
        return []


@dataclasses.dataclass
class ExtendHooks:
    children: List[ManagedHooks]

    def __enter__(self):
        log.info("extending hooks")
        live_hooks.set(self)

    def __exit__(self, type, value, traceback):
        log.info("done extending hooks")
        live_hooks.set(None)
        return False

    def _get_extra_hooks(self, name) -> List[Callable]:
        return flatten([c._get_hooks(name) for c in self.children])


class All(ManagedHooks):
    @property
    def observed(self):
        return self.create_hook("observed")

    @property
    def hold(self):
        return self.create_hook("hold")

    @property
    def enter(self):
        return self.create_hook("enter")


all = All()


def flatten(l):
    return [item for sl in l for item in sl]
