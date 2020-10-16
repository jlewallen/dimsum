from typing import List

import sys
import logging
import datetime
import time
import asyncio
import lupa
import props


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


class Changes:
    def __init__(self):
        self.messages = []

    def msg(self, m):
        self.messages.append(m)

    def __str__(self):
        return str(self.messages)


class Behavior:
    def __init__(self, **kwargs):
        self.lua = kwargs["lua"] if "lua" in kwargs else None
        self.logs = kwargs["logs"] if "logs" in kwargs else []

    def error(self, messages: List[str], error):
        self.logs.extend(messages)

    def done(self, messages: List[str]):
        self.logs.extend(messages)
        self.logs = self.logs[-20:]


GenericThunk = """
function(scope, g)
    return g(scope, scope.world, scope.person)
end
"""


class ScriptEngine:
    def execute(self, thunk: str, scope: Scope, main: Behavior):
        messages: List[str] = []

        def debug(*args):
            message = " ".join(args)
            logging.info(
                "lua:debug:%s: %s"
                % (
                    "",
                    message,
                )
            )
            now = datetime.datetime.now()
            stamped = now.strftime("%Y/%m/%d %H:%M:%S") + " " + message
            messages.append(stamped)

        debug("invoked")

        lua = lupa.LuaRuntime(unpack_returned_tuples=True)
        g = lua.globals()
        g.debug = debug
        for key, value in scope.items():
            g[key] = value
        thunker = lua.eval(thunk)
        fn = lua.eval(main.lua)
        try:
            rv = thunker(scope, fn)
            main.done(messages)
            return rv
        except Exception as err:
            logging.error("error", err)
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
        self.map[name] = Behavior(**kwargs)

    def items(self):
        return self.map.items()

    def replace(self, map):
        typed = {key: Behavior(**value) for key, value in map.items()}
        return super().replace(**typed)


async def tests():
    pass


if __name__ == "__main__":
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    asyncio.run(tests())
