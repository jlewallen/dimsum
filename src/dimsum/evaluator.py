import logging
import lark
import props
import game
import movement
import things
import actions
import finders

log = logging.getLogger("dimsum")


class Evaluate(lark.Transformer):
    def __init__(self, world, player):
        self.world = world
        self.player = player

    def start(self, args):
        return args[0]

    def verbs(self, args):
        return args[0]

    def stimulate(self, args):
        return args[0]

    # Actions

    def look(self, args):
        return actions.Look()

    def drop(self, args):
        return actions.Drop()

    def drop_quantity(self, args):
        return actions.Drop(quantity=args[0], item=args[1])

    def drop_item(self, args):
        return actions.Drop(item=args[0])

    def home(self, args):
        return actions.Home()

    def put_inside(self, args):
        return actions.PutInside(container=args[1], item=args[0])

    def take_out(self, args):
        return actions.TakeOut(container=args[1], item=args[0])

    def open_hands(self, args):
        return actions.Open(item=args[0])

    def close_hands(self, args):
        return actions.Close(item=args[0])

    def lock_new(self, args):
        return actions.Lock(item=args[0], key=finders.FindNone())

    def lock_with(self, args):
        return actions.Lock(item=args[0], key=args[1])

    def unlock(self, args):
        return actions.Unlock(item=args[0], key=finders.AnyHeldItem())

    def unlock_with(self, args):
        return actions.Unlock(item=args[0], key=args[1])

    def hold(self, args):
        return actions.Hold(item=args[0])

    def hold_quantity(self, args):
        return actions.Hold(item=args[1], quantity=args[0])

    def make(self, args):
        return actions.Make(template=args[0])

    def forget(self, args):
        return actions.Forget(name=args[0])

    def climb(self, args):
        return actions.Climb(finder=args[0])

    def run(self, args):
        return actions.Climb(finder=args[0])

    def go(self, args):
        return actions.Go(finder=args[0])

    def walk(self, args):
        return actions.Go(finder=args[0])

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

    def kiss(self, args):
        return actions.Kiss(who=args[0])

    def tickle(self, args):
        return actions.Tickle(who=args[0])

    def kick(self, args):
        return actions.Kick(item=args[0])

    def plant(self, args):
        return actions.Plant(item=args[0])

    def shake(self, args):
        return actions.Shake(item=args[0])

    def hit(self, args):
        return actions.Hit(item=args[0])

    def swing(self, args):
        return actions.Swing(item=args[0])

    def wear(self, args):
        return actions.Wear(item=args[0])

    def remove(self, args):
        return actions.Remove(item=args[0])

    def poke(self, args):
        return actions.Poke(who=args[0])

    def look_item(self, args):
        return actions.Look(item=args[0])

    def look_for(self, args):
        return actions.LookFor(name=str(args[0]))

    def look_inside(self, args):
        return actions.LookInside(item=args[0])

    def say(self, args):
        return actions.Unknown()

    def tell(self, args):
        return actions.Unknown()

    def think(self, args):
        return actions.LookMyself()

    def look_myself(self, args):
        return actions.LookMyself()

    def look_down(self, args):
        return actions.LookDown()

    def auth(self, args):
        return actions.Auth(password=str(args[0]))

    # Item lookup

    def make_quantified(self, args):
        quantity = args[0]
        return actions.Make(template=things.MaybeQuantifiedItem(args[1], quantity))

    def makeable_noun(self, args):
        return finders.MaybeItemOrRecipe(str(args[0]))

    def held_noun(self, args):
        return finders.HeldItem(q=str(args[0]))

    def contained_noun(self, args):
        return finders.ContainedItem(q=str(args[0]))

    def unheld_noun(self, args):
        return finders.UnheldItem(str(args[0]))

    def noun(self, args):
        return finders.AnyItem(str(args[0]))

    def direction(self, args):
        for d in movement.Direction:
            if str(args[0]).lower() == d.name.lower():
                return movement.FindDirectionalRoute(d)
        raise Exception("unknown directional route")

    def route(self, args):
        return args[0]

    def named_route(self, args):
        return movement.FindNamedRoute(str(args[0]))

    def this(self, args):
        return finders.AnyHeldItem()

    def modify_servings(self, args):
        return actions.ModifyServings(item=finders.AnyHeldItem(), number=args[0])

    def modify_field(self, args):
        field = str(args[0])
        value = args[1]
        return actions.ModifyField(item=finders.AnyHeldItem(), field=field, value=value)

    def when_worn(self, args):
        return actions.ModifyActivity(
            item=finders.AnyHeldItem(), activity=props.Worn, value=True
        )

    def when_opened(self, args):
        return actions.ModifyActivity(
            item=finders.AnyHeldItem(), activity=props.Opened, value=True
        )

    def when_eaten(self, args):
        return actions.ModifyActivity(
            item=finders.AnyHeldItem(), activity=props.Eaten, value=True
        )

    def when_drank(self, args):
        return actions.ModifyActivity(
            item=finders.AnyHeldItem(), activity=props.Drank, value=True
        )

    def remember(self, args):
        return actions.Remember()

    def verb(self, args):
        return actions.Unknown()

    def text(self, args):
        return str(args[0])

    def number(self, args):
        return float(args[0])


def create(world, player):
    return Evaluate(world, player)
