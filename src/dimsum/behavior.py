from typing import List, Sequence, Dict
import abc
import sys
import logging
import datetime
import time
import asyncio
import lupa

import properties

log = logging.getLogger("dimsum")


class ConditionalBehavior:
    def __init__(self, **kwargs):
        super().__init__()

    @abc.abstractmethod
    def enabled(self, **kwargs) -> bool:
        raise NotImplementedError

    @abc.abstractmethod
    def lua(self, **kwargs) -> str:
        raise NotImplementedError


class RegisteredBehavior:
    def __init__(self, name: str, behavior: ConditionalBehavior):
        super().__init__()
        self.name = name
        self.behavior = behavior


registered_behaviors: List[RegisteredBehavior] = []


def conditional(name):
    def wrap(klass):
        log.info("registered behavior: %s %s", name, klass)
        registered_behaviors.append(RegisteredBehavior(name, klass()))

    return wrap


class Scope:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    @property
    def map(self):
        return self.__dict__

    def keys(self):
        return self.map.keys()

    def values(self):
        return self.map.values()

    def items(self):
        return self.map.items()

    def extend(self, **kwargs):
        copy = self.__dict__.copy()
        copy.update(**kwargs)
        return Scope(**copy)

    def prepare(self, wrap):
        prepared = {}
        for key, value in self.map.items():
            prepared[key] = wrap(value)
        return prepared


class Changes:
    def __init__(self):
        self.messages = []

    def msg(self, m):
        self.messages.append(m)

    def __str__(self):
        return str(self.messages)


class Behavior:
    def __init__(self, lua=None, logs=None, **kwargs):
        self.lua = lua
        self.logs = logs if logs else []

    def check(self):
        eng = lupa.LuaRuntime(unpack_returned_tuples=True)
        eng.eval(self.lua)

    def error(self, messages: List[str], error):
        self.logs.extend(messages)

    def done(self, messages: List[str]):
        self.logs.extend(messages)
        self.logs = self.logs[-20:]


GenericThunk = """
function(scope, g)
    assert(scope, "scope is required (generic)")
    assert(scope.world, "world is required (generic)")
    assert(scope.area, "area is required (generic)")
    return g(scope, scope.world, scope.area, scope.entity)
end
"""

PersonThunk = """
function(scope, g)
    assert(scope, "scope is required (person)")
    assert(scope.world, "world is required (person)")
    assert(scope.area, "area is required (person)")
    return g(scope, scope.world, scope.area, scope.person)
end
"""


class ScriptEngine:
    def __init__(self):
        self.lua = lupa.LuaRuntime(unpack_returned_tuples=True)
        self.lua.eval("math.randomseed(os.time())")

    def prepare(self, scope: Scope, context_factory):
        ctx = context_factory()
        return scope.prepare(ctx.wrap)

    def execute(self, thunk: str, scope: Scope, main: Behavior):
        messages: List[str] = []

        def debug(*args):
            message = ""
            if isinstance(args, list) or isinstance(args, tuple):
                message = " ".join([str(e) for e in args])
            else:
                raise Exception("unexpected debug")
            log.info("lua:debug: " + message)
            now = datetime.datetime.now()
            stamped = now.strftime("%Y/%m/%d %H:%M:%S") + " " + message
            messages.append(stamped)

        g = self.lua.globals()
        for key, value in scope.items():
            log.debug("lua: %s = %s", key, value)
            g[key] = value
        g.debug = debug

        thunker = self.lua.eval(thunk)
        fn = self.lua.eval(main.lua)
        try:
            rv = thunker(scope, fn)
            main.done(messages)
            return rv
        except Exception as err:
            log.error("error: %s" % (err,), exc_info=True)
            main.error(messages, err)
        return None


# Behavior keys are of the form:
# b:<key>:<behavior>
# The <key> allows multiple customizations, and will be run in order sorted by key.
class BehaviorMap(properties.PropertyMap):
    def get_all(self, behavior: str):
        pattern = "b:(.+):%s" % (behavior,)
        return [self.map[key] for key in self.keys_matching(pattern)]

    def add(self, name, **kwargs):
        b = self.map[name] = Behavior(**kwargs)
        b.check()
        return b

    def items(self):
        return self.map.items()

    def replace(self, map):
        typed = {key: Behavior(**value) for key, value in map.items()}
        for key, value in typed.items():
            value.check()
        return super().replace(**typed)


class BehaviorMixin:
    def __init__(self, behaviors: BehaviorMap = None, **kwargs):
        super().__init__(**kwargs)  # type: ignore
        self.behaviors = behaviors if behaviors else BehaviorMap()

    def get_behaviors(self, name):
        returning = self.behaviors.get_all(name)
        for rb in registered_behaviors:
            if rb.name == name:
                if rb.behavior.enabled(entity=self):
                    returning.append(Behavior(lua=rb.behavior.lua, logs=[]))
        return returning

    def add_behavior(self, name, **kwargs):
        return self.behaviors.add(name, **kwargs)
