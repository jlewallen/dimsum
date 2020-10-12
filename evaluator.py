import lark
import game


class Evaluate(lark.Transformer):
    def __init__(self, world, player):
        self.world = world
        self.player = player

    def something_new(self, args):
        return game.Item(
            owner=self.player, details=game.Details(str(args[0]), str(args[0]))
        )

    def something_here(self, args):
        area, item = self.world.search(self.player, str(args[0]))
        return item

    def somewhere(self, args):
        area, item = self.world.search(self.player, str(args[0]))
        return item

    def make(self, args):
        return game.Make(args[0])

    def drop(self, args):
        return game.Drop()

    def hold(self, args):
        return game.Hold(item=args[0])

    def allow_opening(self, args):
        pass

    def allow_eating(self, args):
        pass

    def text(self, args):
        return str(args[0])

    def number(self, args):
        return float(args[0])

    def go(self, args):
        return game.Go(item=args[0])

    def look(self, args):
        return game.Look()

    def modify_field(self, args):
        area = self.world.find_player_area(self.player)
        item = area
        if len(self.player.holding) == 0:
            if area.owner != self.player:
                raise game.NotHoldingAnything(
                    "you're not holding anything and you don't own this area"
                )
        else:
            item = self.player.holding[0]
        field = str(args[0])
        value = args[1]
        return game.ModifyField(item=item, field=field, value=value)

    def start(self, args):
        return args[0]


def create(world, player):
    return Evaluate(world, player)
