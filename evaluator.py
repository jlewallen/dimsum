import lark
import game


class Evaluate(lark.Transformer):
    def __init__(self, world, player):
        self.world = world
        self.player = player

    def start(self, args):
        return args[0]

    def make(self, args):
        return game.Make(args[0])

    def drop(self, args):
        return game.Drop()

    def home(self, args):
        return game.Home()

    def hold(self, args):
        return game.Hold(item=args[0])

    def somebody_here(self, args):
        area, item = self.world.search(self.player, str(args[0]))
        print(args, item)
        return item

    def item_here(self, args):
        area, item = self.world.search(self.player, str(args[0]))
        return item

    def item_held(self, args):
        return self.world.search_hands(self.player, str(args[0]))

    def item_goes(self, args):
        area, item = self.world.search(self.player, str(args[0]))
        return item

    def item_recipe(self, args):
        name = str(args[0])
        recipe = self.player.find_recipe(name)
        if recipe:
            return recipe.invoke(self.player)
        return game.Item(owner=self.player, details=game.Details(name, name))

    def go(self, args):
        return game.Go(item=args[0])

    def eat(self, args):
        return game.Eat(item=args[0])

    def drink(self, args):
        return game.Drink(item=args[0])

    def look(self, args):
        return game.Look()

    def obliterate(self, args):
        return game.Obliterate()

    def this(self, args):
        return self.get_item_held()

    def call(self, args):
        return game.CallThis(item=args[0], name=str(args[1]))

    def stimulate(self, args):
        return args[0]

    def hug(self, args):
        return game.Hug(who=args[0])

    def heal(self, args):
        return game.Heal(who=args[0])

    def kick(self, args):
        return game.Kick(who=args[0])

    def kiss(self, args):
        return game.Kiss(who=args[0])

    def tickle(self, args):
        return game.Tickle(who=args[0])

    def poke(self, args):
        return game.Poke(who=args[0])

    def look_item(self, args):
        return game.Look(item=args[0])

    def look_myself(self, args):
        return game.Myself()

    def get_item_held(self):
        if len(self.player.holding) == 0:
            raise game.NotHoldingAnything("you're not holding anything")
        return self.player.holding[0]

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

    def when_opened(self, args):
        return game.ModifyActivity(
            item=self.get_item_held(), activity="opened", value=True
        )

    def when_eaten(self, args):
        return game.ModifyActivity(
            item=self.get_item_held(), activity="eaten", value=True
        )

    def when_drank(self, args):
        return game.ModifyActivity(
            item=self.get_item_held(), activity="drank", value=True
        )

    def remember(self, args):
        return game.Remember()

    def text(self, args):
        return str(args[0])

    def number(self, args):
        return float(args[0])


def create(world, player):
    return Evaluate(world, player)
