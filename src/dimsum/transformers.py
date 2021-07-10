import dataclasses
import lark

from model import Entity, World
import finders as finders
import scopes.movement as movement


@dataclasses.dataclass
class Base(lark.Transformer):
    world: World
    player: Entity

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
        for d in movement.Direction:
            if str(args[0]).lower() == d.name.lower():
                return d
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
        return finders.ObjectNumber(int(args[0]))

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
