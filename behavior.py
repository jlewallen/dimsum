import lupa
import game
import props


class Behavior(props.PropertyMap):
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
