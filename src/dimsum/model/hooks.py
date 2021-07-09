import abc
import logging
import dataclasses
import functools
import contextvars

from typing import List, Optional, Callable, Dict
from weakref import ref, ReferenceType

from model.entity import Entity

log = logging.getLogger("dimsum.hooks")
live_hooks: contextvars.ContextVar = contextvars.ContextVar("dimsum:hooks")


@dataclasses.dataclass
class Hook:
    manager: "ManagedHooks"
    name: str
    fn: Optional[Callable] = None
    hooks: List[Callable] = dataclasses.field(default_factory=lambda: [])

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
        log.debug(
            "hook:call '%s' hooks=%s args=%s kwargs=%s", name, hooks, args, kwargs
        )

        for hook_fn in hooks:
            call = functools.partial(hook_fn, call)

        return call(*args, **kwargs)

    def hook(self, fn):
        log.info("hook:hook: %s", fn)
        self.hooks.append(fn)
        return fn


@dataclasses.dataclass
class ManagedHooks:
    everything: Dict[str, Hook] = dataclasses.field(default_factory=dict)

    def create_hook(self, name: str) -> Hook:
        return self.everything.setdefault(name, Hook(self, name))

    def _get_hooks(self, name: str) -> List[Callable]:
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


@dataclasses.dataclass
class All(ManagedHooks):
    @property
    def observed(self):
        return self.create_hook("observed")


all = All()


def flatten(l):
    return [item for sl in l for item in sl]
