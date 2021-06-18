from typing import Any

import os
import hashlib
import base64

import properties
import movement
import health
import mechanics
import finders
import carryable

from context import *
from reply import *
from game import *
from things import *
from envo import *
from living import *
from animals import *
from events import *
from world import *


MemoryAreaKey = "m:area"
log = logging.getLogger("dimsum")


class PersonAction(Action):
    async def perform(self, ctx: Ctx, world: World, player: Player):
        raise NotImplementedError


class Unknown(PersonAction):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def perform(self, ctx: Ctx, world: World, player: Player):
        log.warning("{0} performed".format(self))
        return Failure("sorry, i don't understand")


class Auth(PersonAction):
    def __init__(self, password=None, **kwargs):
        super().__init__(**kwargs)
        self.password = password

    async def perform(self, ctx: Ctx, world: World, player: Player):
        if properties.Password in player.props:
            saltEncoded, keyEncoded = player.props[properties.Password]
            salt = base64.b64decode(saltEncoded)
            key = base64.b64decode(keyEncoded)
            actual_key = hashlib.pbkdf2_hmac(
                "sha256", self.password.encode("utf-8"), salt, 100000
            )

        salt = os.urandom(32)
        key = hashlib.pbkdf2_hmac("sha256", self.password.encode("utf-8"), salt, 100000)
        player.props[properties.Password] = [
            base64.b64encode(salt).decode("utf-8"),
            base64.b64encode(key).decode("utf-8"),
        ]
        return Success("done, https://mud.espial.me")


class Home(PersonAction):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def perform(self, ctx: Ctx, world: World, player: Player):
        await ctx.extend().hook("home:before")
        return await Go(area=world.welcome_area()).perform(ctx, world, player)


class AddItemArea(PersonAction):
    def __init__(self, item=None, area=None, **kwargs):
        super().__init__(**kwargs)
        self.item = item
        self.area = area

    async def perform(self, ctx: Ctx, world: World, player: Player):
        with self.area.make(carryable.ContainingMixin) as ground:
            after_add = ground.add_item(self.item)
            world.register(after_add)

            # We do this after because we may consolidate this Item and
            # this keeps us from having to unregister the item.
            world.register(after_add)

        await world.bus.publish(ItemsAppeared(area=self.area, items=[self.item]))
        await ctx.extend(area=self.area, appeared=[self.item]).hook("appeared:after")
        return Success("%s appeared" % (p.join([self.item]),))


class Make(PersonAction):
    def __init__(
        self,
        template: finders.MaybeItemOrRecipe = None,
        item: things.ItemFinder = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.template = template
        self.item = item

    async def perform(self, ctx: Ctx, world: World, player: Player):
        item: Optional[things.Item] = None
        if self.item:
            item = world.apply_item_finder(player, self.item)

        if self.template:
            item = self.template.create_item(
                person=player, creator=player, owner=player
            )
            assert isinstance(item, things.Item)

        if not item:
            return Failure("make what now?")

        with player.make(carryable.ContainingMixin) as contain:
            after_hold = contain.hold(item)
            # We do this after because we may consolidate this Item and
            # this keeps us from having to unregister the item.
            world.register(after_hold)

        area = world.find_player_area(player)
        await world.bus.publish(ItemsMade(person=player, area=area, items=[after_hold]))
        return Success("you're now holding %s" % (after_hold,), item=after_hold)


class Wear(PersonAction):
    def __init__(self, item: things.ItemFinder = None, **kwargs):
        super().__init__(**kwargs)
        assert item
        self.item = item

    async def perform(self, ctx: Ctx, world: World, player: Player):
        item = world.apply_item_finder(player, self.item)
        if not item:
            return Failure("wear what?")

        with item.make(mechanics.InteractableMixin) as inaction:
            if not inaction.when_worn():
                return Failure("you can't wear that")

        with player.make(carryable.ContainingMixin) as contain:
            assert contain.is_holding(item)

            with player.make(apparel.ApparelMixin) as wearing:
                if wearing.wear(item):
                    contain.drop(item)

        # TODO Publish
        await ctx.extend(wear=[item]).hook("wear:after")
        return Success("you wore %s" % (item))


class Remove(PersonAction):
    def __init__(self, item: things.ItemFinder = None, **kwargs):
        super().__init__(**kwargs)
        assert item
        self.item = item

    async def perform(self, ctx: Ctx, world: World, player: Player):
        item = world.apply_item_finder(player, self.item)
        if not item:
            return Failure("remove what?")

        with player.make(apparel.ApparelMixin) as wearing:
            if not wearing.is_wearing(item):
                return Failure("you aren't wearing that")

            assert wearing.is_wearing(item)

            if wearing.unwear(item):
                with player.make(carryable.ContainingMixin) as contain:
                    contain.hold(item)

        await ctx.extend(remove=[item]).hook("remove:after")
        return Success("you removed %s" % (item))


class Eat(PersonAction):
    def __init__(self, item: things.ItemFinder = None, **kwargs):
        super().__init__(**kwargs)
        assert item
        self.item = item

    async def perform(self, ctx: Ctx, world: World, player: Player):
        item = world.apply_item_finder(player, self.item)
        if not item:
            return Failure("dunno where that is")

        with item.make(mechanics.InteractableMixin) as inaction:
            if not inaction.when_eaten():
                return Failure("you can't eat that")

        area = world.find_player_area(player)
        with player.make(health.HealthMixin) as p:
            await p.consume(item, area=area, ctx=ctx)
        await ctx.extend(eat=item).hook("eat:after")

        return Success("you ate %s" % (item))


class Drink(PersonAction):
    def __init__(self, item: things.ItemFinder = None, **kwargs):
        super().__init__(**kwargs)
        assert item
        self.item = item

    async def perform(self, ctx: Ctx, world: World, player: Player):
        item = world.apply_item_finder(player, self.item)
        if not item:
            return Failure("dunno where that is")

        with item.make(mechanics.InteractableMixin) as inaction:
            if not inaction.when_drank():
                return Failure("you can't drink that")

        area = world.find_player_area(player)
        with player.make(health.HealthMixin) as p:
            await p.consume(item, area=area, ctx=ctx)
        await ctx.extend(eat=item).hook("drink:after")

        return Success("you drank %s" % (item))


class Join(PersonAction):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def perform(self, ctx: Ctx, world: World, player: Player):
        world.register(player)
        await world.bus.publish(PlayerJoined(player=player))
        await ctx.hook("entered:before")
        with world.welcome_area().make(occupyable.OccupyableMixin) as area:
            await area.entered(world.bus, player)
        await ctx.hook("entered:after")
        return Success("welcome!")


class LookInside(PersonAction):
    def __init__(self, item: things.ItemFinder = None, **kwargs):
        super().__init__(**kwargs)
        assert item
        self.item = item

    async def perform(self, ctx: Ctx, world: World, player: Player):
        item = world.apply_item_finder(player, self.item)
        if not item:
            return Failure("inside what?")

        with item.make(carryable.ContainingMixin) as contain:
            if not contain.is_open():
                return Failure("you can't do that")

            return EntitiesObservation(things.expected(contain.holding))


class LookFor(PersonAction):
    def __init__(self, item: things.ItemFinder = None, **kwargs):
        super().__init__(**kwargs)
        assert item
        self.item = item

    async def perform(self, ctx: Ctx, world: World, player: Player):
        item = world.apply_item_finder(player, self.item)
        if not item:
            return Failure("i can't seem to find that")

        with player.make(mechanics.VisibilityMixin) as vis:
            vis.add_observation(item.identity)

        with player.make(carryable.ContainingMixin) as contain:
            await ctx.extend(holding=contain.holding, item=item).hook("look-for")
            return EntitiesObservation([item])


class LookMyself(PersonAction):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def perform(self, ctx: Ctx, world: World, player: Player):
        await ctx.hook("look-myself")
        return PersonalObservation(player)


class LookDown(PersonAction):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def perform(self, ctx: Ctx, world: World, player: Player):
        await ctx.hook("look-down")
        with player.make(carryable.ContainingMixin) as contain:
            return EntitiesObservation(things.expected(contain.holding))


class Look(PersonAction):
    def __init__(self, item=None, **kwargs):
        super().__init__(**kwargs)
        self.item = item

    async def perform(self, ctx: Ctx, world: World, player: Player):
        if self.item:
            return DetailedObservation(ObservedItem(self.item))
        log.info("person: %s %s", player.key, player)

        area = world.find_player_area(player)
        assert area
        return AreaObservation(area, player)


class Drop(PersonAction):
    def __init__(self, item: things.ItemFinder = None, quantity: int = None, **kwargs):
        super().__init__(**kwargs)
        self.quantity = quantity if quantity else None
        self.item = item if item else None

    async def perform(self, ctx: Ctx, world: World, player: Player):
        item = None

        if self.item:
            item = world.apply_item_finder(player, self.item)
            if not item:
                return Failure("drop what?")

        area = world.find_player_area(player)

        with player.make(carryable.ContainingMixin) as contain:
            dropped, failure = contain.drop_here(
                area,
                item,
                quantity=self.quantity,
                creator=player,
                owner=player,
                ctx=ctx,
            )
            log.info("DROPPED = %s", [e.kind for e in dropped])
            if dropped:
                area = world.find_player_area(player)
                await world.bus.publish(
                    ItemsDropped(person=player, area=area, dropped=dropped)
                )
                await ctx.extend(dropped=dropped).hook("drop:after")
                return Success("you dropped %s" % (p.join(dropped),))

            return Failure(failure)


class Hold(PersonAction):
    def __init__(self, item: things.ItemFinder = None, quantity: int = None, **kwargs):
        super().__init__(**kwargs)
        assert item
        self.item = item
        self.quantity = quantity

    async def perform(self, ctx: Ctx, world: World, player: Player):
        item = world.apply_item_finder(player, self.item)
        if not item:
            return Failure("sorry, hold what?")

        with player.make(carryable.ContainingMixin) as pockets:
            # This should happen after? What if there's more on the ground?
            if pockets.is_holding(item):
                return Failure("you're already holding that")

            area = world.find_player_area(player)
            with area.make(carryable.ContainingMixin) as ground:
                if self.quantity:
                    with item.make(carryable.CarryableMixin) as hands:
                        removed = hands.separate(
                            self.quantity, creator=player, owner=player, ctx=ctx
                        )
                        if hands.quantity == 0:
                            world.unregister(item)
                            ground.drop(item)
                    item = removed[0]
                else:
                    ground.unhold(item)

                after_hold = pockets.hold(item)
                if after_hold != item:
                    world.unregister(item)
                await world.bus.publish(
                    ItemHeld(person=player, area=area, hold=[after_hold])
                )
                await ctx.extend(hold=[after_hold]).hook("hold:after")
                return Success("you picked up %s" % (after_hold,), item=after_hold)


class Open(PersonAction):
    def __init__(self, item: things.ItemFinder = None, **kwargs):
        super().__init__(**kwargs)
        assert item
        self.item = item

    async def perform(self, ctx: Ctx, world: World, player: Player, **kwargs):
        item = world.apply_item_finder(player, self.item)
        if not item:
            return Failure("open what?")

        with item.make(carryable.ContainingMixin) as contain:
            if not contain.can_hold():
                return Failure("you can't open that")

            if not contain.open():
                return Failure("huh, won't open")

        return Success("opened")


class Close(PersonAction):
    def __init__(self, item: things.ItemFinder = None, **kwargs):
        super().__init__(**kwargs)
        assert item
        self.item = item

    async def perform(self, ctx: Ctx, world: World, player: Player, **kwargs):
        item = world.apply_item_finder(player, self.item)
        if not item:
            return Failure("close what?")

        with item.make(carryable.ContainingMixin) as contain:
            if not contain.can_hold():
                return Failure("you can't open that")

            if not contain.close():
                return Failure("it's got other plans")

        return Success("closed")


class Lock(PersonAction):
    def __init__(
        self, item: things.ItemFinder = None, key: things.ItemFinder = None, **kwargs
    ):
        super().__init__(**kwargs)
        assert item
        self.item = item
        assert key
        self.key = key

    async def perform(self, ctx: Ctx, world: World, player: Player, **kwargs):
        area = world.find_player_area(player)

        item = world.apply_item_finder(player, self.item)
        if not item:
            return Failure("what?")

        maybe_key = world.apply_item_finder(player, self.key, exclude=[item])

        with player.make(carryable.ContainingMixin) as hands:
            with item.make(carryable.ContainingMixin) as locking:
                locked_with = locking.lock(
                    key=maybe_key, creator=player, owner=player, **kwargs
                )
                if not locked_with:
                    return Failure("can't seem to lock that")

                assert locking.is_locked()
                hands.hold(locked_with)

        return Success("done")


class Unlock(PersonAction):
    def __init__(
        self, item: things.ItemFinder = None, key: things.ItemFinder = None, **kwargs
    ):
        super().__init__(**kwargs)
        assert item
        self.item = item
        assert key
        self.key = key

    async def perform(self, ctx: Ctx, world: World, player: Player, **kwargs):
        area = world.find_player_area(player)

        item = world.apply_item_finder(player, self.item)
        if not item:
            return Failure("unlock what?")

        log.info("finding key %s", self.key)
        maybe_key = world.apply_item_finder(player, self.key, exclude=[item])
        log.info("maybe key: %s", maybe_key)
        with item.make(carryable.ContainingMixin) as unlocking:
            if unlocking.unlock(key=maybe_key, **kwargs):
                return Success("done")
        return Failure("nope")


class PutInside(PersonAction):
    def __init__(
        self,
        container: things.ItemFinder = None,
        item: things.ItemFinder = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        assert container
        self.container = container
        assert item
        self.item = item

    async def perform(self, ctx: Ctx, world: World, player: Player, **kwargs):
        area = world.find_player_area(player)

        container = world.apply_item_finder(player, self.container)
        if not container:
            return Failure("what?")

        with container.make(carryable.ContainingMixin) as containing:
            if not containing.can_hold():
                return Failure("inside... that?")

            item = world.apply_item_finder(player, self.item)
            if not item:
                return Failure("what?")

            if containing.place_inside(item):
                with player.make(carryable.ContainingMixin) as pockets:
                    pockets.drop(item)
                return Success("inside, done")

        return Failure("you can't do that")


class TakeOut(PersonAction):
    def __init__(
        self,
        container: things.ItemFinder = None,
        item: things.ItemFinder = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        assert container
        self.container = container
        assert item
        self.item = item

    async def perform(self, ctx: Ctx, world: World, player: Player, **kwargs):
        area = world.find_player_area(player)

        container = world.apply_item_finder(player, self.container)
        if not container:
            return Failure("what?")

        with container.make(carryable.ContainingMixin) as containing:
            if not containing.can_hold():
                return Failure("outside of... that?")

            item = world.apply_item_finder(player, self.item)
            if not item:
                return Failure("what?")

            if containing.take_out(item):
                with player.make(carryable.ContainingMixin) as pockets:
                    pockets.hold(item)
                return Success("done, you're holding that now")

        return Failure("doesn't seem like you can")


class MovingAction(PersonAction):
    def __init__(
        self, area: envo.Area = None, finder: movement.FindsRoute = None, **kwargs
    ):
        super().__init__(**kwargs)
        self.area = area
        self.finder = finder

    async def move(self, ctx: Ctx, world: World, player: Player, verb=DefaultMoveVerb):
        area = world.find_player_area(player)

        destination = self.area

        if self.finder:
            log.info("finder: {0}".format(self.finder))
            area = world.find_player_area(player)
            route = await self.finder.find_route(
                area, player, world=world, verb=verb, builder=world
            )
            if route:
                routed: Any = route.area
                destination = routed

        if destination is None:
            return Failure("where?")

        with destination.make(occupyable.OccupyableMixin) as entering:
            with area.make(occupyable.OccupyableMixin) as leaving:
                await ctx.extend(area=area).hook("left:before")
                await leaving.left(world.bus, player)
                await ctx.extend(area=area).hook("left:after")

                await ctx.extend(area=destination).hook("entered:before")
                await entering.entered(world.bus, player)
                await ctx.extend(area=destination).hook("entered:after")

        return AreaObservation(world.find_player_area(player), player)


class Climb(MovingAction):
    async def perform(self, ctx: Ctx, world: World, player: Player):
        # If climb ever becomes a string outside of this function, rethink.
        return await self.move(ctx, world, player, verb="climb")


class Go(MovingAction):
    async def perform(self, ctx: Ctx, world: World, player: Player):
        return await self.move(ctx, world, player)


class Obliterate(PersonAction):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def perform(self, ctx: Ctx, world: World, player: Player):
        area = world.find_player_area(player)
        items = None
        with player.make(carryable.ContainingMixin) as pockets:
            items = things.expected(pockets.drop_all())
        if len(items) == 0:
            return Failure("you're not holding anything")

        item: Any = None  # TODO CarryableMixin to Entity

        for item in items:
            item.try_modify()

        for item in items:
            world.unregister(item)
            await world.bus.publish(
                ItemObliterated(person=player, area=area, item=item)
            )

        await ctx.extend(obliterate=items).hook("obliterate:after")

        return Success("you obliterated %s" % (p.join(list(map(str, items))),))


class CallThis(PersonAction):
    def __init__(self, name: str = None, item: things.ItemFinder = None, **kwargs):
        super().__init__(**kwargs)
        assert item
        self.item = item
        assert name
        self.name = name

    async def perform(self, ctx: Ctx, world: World, player: Player):
        item = world.apply_item_finder(player, self.item)
        if not item:
            return Failure("you don't have anything")

        item.try_modify()

        # Copy all of the base props from the item. Exclude stamps.
        template = item
        recipe = Recipe(
            creator=player,
            owner=player,
            props=item.props.clone(),
            behaviors=item.behaviors,
            kind=item.kind,
            template=template,
        )
        world.register(recipe)
        with player.make(mechanics.MemoryMixin) as brain:
            brain.memorize("r:" + self.name, recipe)
        return Success(
            "cool, you'll be able to make another %s easier now" % (self.name,)
        )


class Forget(PersonAction):
    def __init__(self, name=None, **kwargs):
        super().__init__(**kwargs)
        self.name = name

    async def perform(self, ctx: Ctx, world: World, player: Player):
        with player.make(mechanics.MemoryMixin) as brain:
            if self.name in brain.brain:
                brain.forget(self.name)
                return Success("oh wait, was that important?")
        return Failure("huh, seems i already have forgotten that!")


class Remember(PersonAction):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def perform(self, ctx: Ctx, world: World, player: Player):
        area = world.find_player_area(player)
        with player.make(mechanics.MemoryMixin) as brain:
            brain.memorize(MemoryAreaKey, area)
        return Success("you'll be able to remember this place, oh yeah")


class ModifyHardToSee(PersonAction):
    def __init__(self, item: things.ItemFinder = None, hard_to_see=False, **kwargs):
        super().__init__(**kwargs)
        assert item
        self.item = item
        self.hard_to_see = hard_to_see

    async def perform(self, ctx: Ctx, world: World, player: Player):
        item = world.apply_item_finder(player, self.item)
        if not item:
            return Failure("of what?")

        item.try_modify()

        with item.make(mechanics.VisibilityMixin) as vis:
            if self.hard_to_see:
                vis.make_hard_to_see()
            else:
                vis.make_easy_to_see()

        return Success("done")


class ModifyField(PersonAction):
    def __init__(self, item=None, field=None, value=None, **kwargs):
        super().__init__(**kwargs)
        self.item = item
        self.field = field
        self.value = value

    async def perform(self, ctx: Ctx, world: World, player: Player):
        item = world.apply_item_finder(player, self.item)
        if not item:
            return Failure("of what?")

        item.try_modify()

        if self.field in health.NutritionFields:
            with item.make(health.EdibleMixin) as i:
                i.nutrition.properties[self.field] = self.value
        else:
            item.props.set(self.field, self.value)
        return Success("done")


class ModifyActivity(PersonAction):
    def __init__(
        self, item: things.ItemFinder = None, activity=None, value=None, **kwargs
    ):
        super().__init__(**kwargs)
        assert item
        self.item = item
        assert activity
        self.activity = activity
        assert value
        self.value = value

    async def perform(self, ctx: Ctx, world: World, player: Player):
        item = world.apply_item_finder(player, self.item)
        if not item:
            return Failure("of what?")

        item.try_modify()
        with item.make(mechanics.InteractableMixin) as inaction:
            inaction.link_activity(self.activity, self.value)
        item.props.set(self.activity, self.value)
        return Success("done")


class ModifyServings(PersonAction):
    def __init__(self, item: things.ItemFinder = None, number=None, **kwargs):
        super().__init__(**kwargs)
        assert item
        self.item = item
        assert number
        self.number = number

    async def perform(self, ctx: Ctx, world: World, player: Player):
        item = world.apply_item_finder(player, self.item)
        if not item:
            return Failure("nothing to modify")
        item.try_modify()
        with item.make(health.EdibleMixin) as edible:
            edible.modify_servings(self.number)
        return Success("done")


class ModifyCapacity(PersonAction):
    def __init__(self, item: things.ItemFinder = None, capacity=None, **kwargs):
        super().__init__(**kwargs)
        assert item
        self.item = item
        assert capacity
        self.capacity = capacity

    async def perform(self, ctx: Ctx, world: World, player: Player):
        item = world.apply_item_finder(player, self.item)
        if not item:
            return Failure("nothing to modify")
        item.try_modify()
        with item.make(carryable.ContainingMixin) as contain:
            if contain.adjust_capacity(self.capacity):
                return Success("done")
        return Failure("no way")


PourVerb = "pour"


class Pour(PersonAction):
    def __init__(
        self,
        item: things.ItemFinder = None,
        source: things.ItemFinder = None,
        destination: things.ItemFinder = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.item = item
        assert source
        self.source = source
        assert destination
        self.destination = destination

    async def perform(self, ctx: Ctx, world: World, player: Player):
        source = world.apply_item_finder(player, self.source)
        if not source:
            return Failure("from what?")

        destination = world.apply_item_finder(
            player, self.destination, exclude=[source]
        )
        if not destination:
            return Failure("into what?")

        with source.make(carryable.ContainingMixin) as produces:
            if not PourVerb in produces.produces:
                return Failure("you can't pour from that")

            produced = produces.produce_into(
                PourVerb, destination, person=player, creator=player, owner=player
            )
            if produced:
                return Success("done")

        return Failure("oh no")


class PourProducer(carryable.Producer):
    def __init__(self, template: finders.MaybeItemOrRecipe = None, **kwargs):
        super().__init__(**kwargs)  # type: ignore
        assert template
        self.template: finders.MaybeItemOrRecipe = template

    def produce_item(self, **kwargs) -> entity.Entity:
        item = self.template.create_item(verb=PourVerb, **kwargs)
        with item.make(mechanics.InteractableMixin) as inaction:
            inaction.link_activity(properties.Drank)
        with item.make(carryable.CarryableMixin) as carry:
            carry.loose = True
        return item


class ModifyPours(PersonAction):
    def __init__(
        self,
        item: things.ItemFinder = None,
        produces: finders.MaybeItemOrRecipe = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        assert item
        self.item = item
        assert produces
        self.produces = produces

    async def perform(self, ctx: Ctx, world: World, player: Player):
        item = world.apply_item_finder(player, self.item)
        if not item:
            return Failure("nothing to modify")

        log.info("modifying %s to produce %s", item, self.produces)

        item.try_modify()
        with item.make(carryable.ContainingMixin) as produces:
            produces.produces_when(PourVerb, PourProducer(template=self.produces))

        return Success("done")


class ItemsAppeared(Event):
    pass


class Freeze(PersonAction):
    def __init__(self, item: things.ItemFinder = None, **kwargs):
        super().__init__(**kwargs)
        assert item
        self.item = item

    async def perform(self, ctx: Ctx, world: World, player: Player, **kwargs):
        item = world.apply_item_finder(player, self.item)
        if not item:
            return Failure("freeze what?")

        if not item.can_modify():
            return Failure("already frozen, pal")

        if not item.freeze(player.identity):
            return Failure("you can't do that!")

        return Success("frozen")


class Unfreeze(PersonAction):
    def __init__(self, item: things.ItemFinder = None, **kwargs):
        super().__init__(**kwargs)
        assert item
        self.item = item

    async def perform(self, ctx: Ctx, world: World, player: Player, **kwargs):
        item = world.apply_item_finder(player, self.item)
        if not item:
            return Failure("unfreeze what?")

        if item.can_modify():
            return Failure("why do that?")

        if not item.unfreeze(player.identity):
            return Failure("you can't do that! is that yours?")

        return Success("unfrozen")
