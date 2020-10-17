from typing import List, Sequence, Dict

import sys
import logging
import datetime
import time
import asyncio
import lupa

import props

log = logging.getLogger("dimsum")


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
    return g(scope, scope.world, scope.area, scope.entity)
end
"""

PersonThunk = """
function(scope, g)
    return g(scope, scope.world, scope.area, scope.person)
end
"""


class ScriptEngine:
    def __init__(self):
        self.lua = lupa.LuaRuntime(unpack_returned_tuples=True)

    def prepare(self, scope: Scope, wrap):
        return scope.prepare(wrap)

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

        debug("invoked")

        g = self.lua.globals()
        g.debug = debug
        for key, value in scope.items():
            g[key] = value
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
class BehaviorMap(props.PropertyMap):
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
