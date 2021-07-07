import logging
import lark

import model.game as game
import model.things as things
import model.finders as finders
import model.properties as properties
import model.scopes.movement as movement

import plugins.default.actions as actions

import transformers

log = logging.getLogger("dimsum")


class Transformer(transformers.Base):
    # Item lookup

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

    def find_direction(self, args):
        return movement.FindDirectionalRoute(args[0])

    def find_route_by_gid(self, args):
        return movement.FindNavigableItem(args[0])

    def route(self, args):
        return args[0]

    def named_route(self, args):
        return movement.FindNamedRoute(str(args[0]))


class Default(Transformer):
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

    def freeze(self, args):
        return actions.Freeze(item=args[0])

    def unfreeze(self, args):
        return actions.Unfreeze(item=args[0])

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

    def forget(self, args):
        return actions.Forget(name=args[0])

    def go(self, args):
        return actions.Go(finder=args[0])

    def eat(self, args):
        return actions.Eat(item=args[0])

    def drink(self, args):
        return actions.Drink(item=args[0])

    def pour(self, args):
        return actions.Pour(
            item=args[0], source=args[1], destination=finders.FindHeldContainer()
        )

    def pour_from(self, args):
        return actions.Pour(source=args[0], destination=finders.FindHeldContainer())

    def wear(self, args):
        return actions.Wear(item=args[0])

    def remove(self, args):
        return actions.Remove(item=args[0])

    def look_item(self, args):
        return actions.Look(item=args[0])

    def look_for(self, args):
        return actions.LookFor(item=args[0])

    def look_inside(self, args):
        return actions.LookInside(item=args[0])

    def think(self, args):
        return actions.LookMyself()

    def look_myself(self, args):
        return actions.LookMyself()

    def look_down(self, args):
        return actions.LookDown()

    def auth(self, args):
        return actions.Auth(password=str(args[0]))

    def when_pours(self, args):
        return actions.ModifyPours(item=finders.AnyHeldItem(), produces=args[0])

    def modify_hard_to_see(self, args):
        return actions.ModifyHardToSee(item=finders.AnyHeldItem(), hard_to_see=True)

    def modify_easy_to_see(self, args):
        return actions.ModifyHardToSee(item=finders.AnyHeldItem(), hard_to_see=False)

    def modify_servings(self, args):
        return actions.ModifyServings(item=finders.AnyHeldItem(), number=args[0])

    def modify_capacity(self, args):
        return actions.ModifyCapacity(item=finders.AnyHeldItem(), capacity=args[0])

    def modify_field(self, args):
        field = str(args[0])
        value = args[1]
        return actions.ModifyField(item=finders.AnyHeldItem(), field=field, value=value)

    def when_worn(self, args):
        return actions.ModifyActivity(
            item=finders.AnyHeldItem(), activity=properties.Worn, value=True
        )

    def when_opened(self, args):
        return actions.ModifyActivity(
            item=finders.AnyHeldItem(), activity=properties.Opened, value=True
        )

    def when_eaten(self, args):
        return actions.ModifyActivity(
            item=finders.AnyHeldItem(), activity=properties.Eaten, value=True
        )

    def when_drank(self, args):
        return actions.ModifyActivity(
            item=finders.AnyHeldItem(), activity=properties.Drank, value=True
        )

    def remember(self, args):
        return actions.Remember()
