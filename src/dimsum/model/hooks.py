import abc
import dataclasses
import functools
import inspect
import contextvars
import asyncio
from typing import List, Optional, Callable, Dict, Any

from loggers import get_logger

from .conditions import Condition
from .context import get

log = get_logger("dimsum.hooks")
live_hooks: contextvars.ContextVar = contextvars.ContextVar("dimsum:hooks")

HookFunction = Callable


class ArgumentTransformer:
    def transform(
        self, fn: Callable, args: List[Any], kwargs: Dict[str, Any]
    ) -> List[Any]:
        return args


@dataclasses.dataclass
class InvokeHook:
    args: ArgumentTransformer = dataclasses.field(default_factory=ArgumentTransformer)

    def chain_hook_call(self, fn: HookFunction, resume: HookFunction):
        def wrap_hook_call(
            hook_fn: HookFunction, resume_fn: HookFunction, *args, **kwargs
        ):
            all_args = [resume_fn] + list(args)
            return hook_fn(*all_args, **kwargs)

        return functools.partial(wrap_hook_call, fn, resume)


@dataclasses.dataclass
class RegisteredHook:
    invoker: InvokeHook
    fn: Callable
    condition: Optional[Condition] = None


@dataclasses.dataclass
class Hook:
    manager: "ManagedHooks"
    name: str
    fn: Optional[Callable] = None
    hooks: List[RegisteredHook] = dataclasses.field(default_factory=lambda: [])

    def target(self, fn):
        log.debug("hook:target: %s", fn)

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

    def _invoke(self, name, call, hooks, args, kwargs):
        log.debug(
            "hook:call '%s' hooks=%s args=%s kwargs=%s", name, hooks, args, kwargs
        )

        for registered in hooks:
            if registered.condition:
                if not registered.condition.applies():
                    continue

            call = registered.invoker.chain_hook_call(registered.fn, call)

        return call(*args, **kwargs)

    def hook(self, wrapped=None, condition: Optional[Condition] = None):
        if wrapped is None:
            return functools.partial(self.hook, condition=condition)

        self.hooks.append(
            RegisteredHook(
                self.manager.invoker,
                self.manager.wrapper_factory(wrapped)
                if self.manager.wrapper_factory
                else wrapped,
                condition,
            )
        )

        def wrap(fn):
            return fn

        return wrap


@dataclasses.dataclass
class ManagedHooks:
    invoker: InvokeHook = dataclasses.field(default_factory=InvokeHook)
    wrapper_factory: Optional[Callable] = dataclasses.field(repr=False, default=None)
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
        log.debug("extending hooks")
        live_hooks.set(self)

    def __exit__(self, type, value, traceback):
        log.debug("done extending hooks")
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
    def drop(self):
        return self.create_hook("drop")

    @property
    def enter(self):
        return self.create_hook("enter")

    @property
    def open(self):
        return self.create_hook("open")

    @property
    def close(self):
        return self.create_hook("close")


all = All()


def flatten(l):
    return [item for sl in l for item in sl]
