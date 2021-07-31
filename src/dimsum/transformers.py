import dataclasses
import lark

from model import Entity, World, FindObjectByGid, FindCurrentArea, FindCurrentPerson
import finders as finders
import scopes.movement as movement


@dataclasses.dataclass
class Base(lark.Transformer):
    world: World
    person: Entity

    def start(self, args):
        return args[0]

    def verbs(self, args):
        return args[0]

    def quoted_string(self, args):
        return args[0][1:-1]

    def string(self, args):
        return args[0]

    def text(self, args):
        return str(args[0])

    def number(self, args):
        return float(args[0])

    def this(self, args):
        return finders.AnyHeldItem()

    def direction(self, args):
        value = str(args[0]).lower()
        for d in movement.Direction:
            if value == d.name.lower():
                return d
        shorthands = {
            "ne": movement.Direction.NORTH_EAST,
            "nw": movement.Direction.NORTH_WEST,
            "se": movement.Direction.SOUTH_EAST,
            "sw": movement.Direction.SOUTH_WEST,
            "northeast": movement.Direction.NORTH_EAST,
            "northwest": movement.Direction.NORTH_WEST,
            "southeast": movement.Direction.SOUTH_EAST,
            "southwest": movement.Direction.SOUTH_WEST,
        }
        if value in shorthands:
            return shorthands[value]
        raise Exception("unknown movement.Direction")

    # Would love to move these closer to creation.
    def makeable_noun(self, args):
        return finders.MaybeItemOrRecipe(str(args[0]))

    def makeable(self, args):
        return args[0]

    # Reasonable to share?
    def noun(self, args):
        return args[0]

    def general_noun(self, args):
        return finders.AnyItem(str(args[0]))

    def object_by_gid(self, args):
        return FindObjectByGid(int(args[0]))

    def consumable_noun(self, args):
        return finders.AnyConsumableItem(q=str(args[0]))

    def held_noun(self, args):
        return finders.HeldItem(q=str(args[0]))

    def contained_noun(self, args):
        return finders.ContainedItem(q=str(args[0]))

    def unheld_noun(self, args):
        return finders.UnheldItem(str(args[0]))

    def contained(self, args):
        return args[0]

    def consumable(self, args):
        return args[0]

    def held(self, args):
        return args[0]

    def unheld(self, args):
        return args[0]

    def here(self, args):
        return FindCurrentArea()

    def myself(self, args):
        return FindCurrentPerson()
