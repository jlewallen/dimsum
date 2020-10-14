import sys
import logging
import asyncio
import lupa
import props


class Scope:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    @property
    def map(self):
        return self.__dict__

    def items(self):
        return self.map.items()


class Changes:
    def __init__(self):
        self.messages = []

    def msg(self, m):
        self.messages.append(m)

    def __str__(self):
        return str(self.messages)


ThunkWorldPersonScope = """
function(scope, g)
   return g(scope, scope.world, scope.person)
end
"""


class ScriptEngine:
    def execute(self, thunk, scope, main):
        lua = lupa.LuaRuntime(unpack_returned_tuples=True)
        g = lua.globals()
        for key, value in scope.items():
            g[key] = value
        thunker = lua.eval(thunk)
        fn = lua.eval(main)
        return thunker(scope, fn)


# Behavior keys are of the form:
# b:<key>:<behavior>
# The <key> allows multiple customizations, and will be run in order sorted by key.
class BehaviorMap(props.PropertyMap):
    def get_all(self, behavior: str):
        for key in self.keys_matching("b:(.+):%s" % (behavior,)):
            print(key)


class Behavior:
    def __init__(self, world, person):
        self.world = world
        self.person = person

    def execute(self, hook):
        lua = lupa.LuaRuntime(unpack_returned_tuples=True)
        g = lua.globals()
        g.world = self.world
        g.player = self.jacob
        g.item = None


class Hook:
    def __init__(self, **kwargs):
        self.item = kwargs["item"] if "item" in kwargs else None

    def prepare(self):
        pass

    def execute(self):
        pass


class CreatedHook(Hook):
    pass


class HeldHook(Hook):
    pass


class DropHook(Hook):
    pass


async def tests():
    pass


if __name__ == "__main__":
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    asyncio.run(tests())
