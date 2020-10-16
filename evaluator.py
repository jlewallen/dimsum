import lark
import game
import actions


class Evaluate(lark.Transformer):
    def __init__(self, world, player):
        self.world = world
        self.player = player

    def start(self, args):
        return args[0]

    def stimulate(self, args):
        return args[0]

    # Actions

    def look(self, args):
        return actions.Look()

    def drop(self, args):
        return actions.Drop()

    def home(self, args):
        return actions.Home()

    def hold(self, args):
        return actions.Hold(item=args[0])

    def make(self, args):
        return actions.Make(args[0])

    def forget(self, args):
        return actions.Forget(name=args[0])

    def go(self, args):
        return actions.Go(item=args[0])

    def eat(self, args):
        return actions.Eat(item=args[0])

    def drink(self, args):
        return actions.Drink(item=args[0])

    def obliterate(self, args):
        return actions.Obliterate()

    def call(self, args):
        return actions.CallThis(item=args[0], name=str(args[1]))

    def hug(self, args):
        return actions.Hug(who=args[0])

    def heal(self, args):
        return actions.Heal(who=args[0])

    def kick(self, args):
        return actions.Kick(who=args[0])

    def kiss(self, args):
        return actions.Kiss(who=args[0])

    def tickle(self, args):
        return actions.Tickle(who=args[0])

    def poke(self, args):
        return actions.Poke(who=args[0])

    def look_item(self, args):
        return actions.Look(item=args[0])

    def look_for(self, args):
        return actions.LookFor(name=str(args[0]))

    def say(self, args):
        return actions.Unknown()

    def tell(self, args):
        return actions.Unknown()

    def think(self, args):
        return actions.Myself()

    def look_myself(self, args):
        return actions.LookMyself()

    def look_down(self, args):
        return actions.LookDown()

    def auth(self, args):
        return actions.Auth(password=str(args[0]))

    # Item lookup

    def noun(self, args):
        area, item = self.world.search(self.player, str(args[0]))
        return item

    def this(self, args):
        return self.get_item_held()

    def item_recipe(self, args):
        name = str(args[0])
        recipe = self.player.find_recipe(name)
        if recipe:
            return recipe.invoke(self.player)
        return game.Item(owner=self.player, details=game.Details(name))

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
        return actions.ModifyField(item=item, field=field, value=value)

    def when_opened(self, args):
        return actions.ModifyActivity(
            item=self.get_item_held(), activity="opened", value=True
        )

    def when_eaten(self, args):
        return actions.ModifyActivity(
            item=self.get_item_held(), activity="eaten", value=True
        )

    def when_drank(self, args):
        return actions.ModifyActivity(
            item=self.get_item_held(), activity="drank", value=True
        )

    def remember(self, args):
        return actions.Remember()

    def verb(self, args):
        return actions.Unknown()

    def text(self, args):
        return str(args[0])

    def number(self, args):
        return float(args[0])

    # Tools

    def get_item_held(self):
        if len(self.player.holding) == 0:
            return None
        return self.player.holding[0]


def create(world, player):
    return Evaluate(world, player)
