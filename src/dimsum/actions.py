from typing import Any

import os
import hashlib
import base64

import props
import movement
import health

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
        return Failure("sorry, i don't understand")


class Auth(PersonAction):
    def __init__(self, password=None, **kwargs):
        super().__init__(**kwargs)
        self.password = password

    async def perform(self, ctx: Ctx, world: World, player: Player):
        if "s:password" in player.details.map:
            saltEncoded, keyEncoded = player.details.map["s:password"]
            salt = base64.b64decode(saltEncoded)
            key = base64.b64decode(keyEncoded)
            actual_key = hashlib.pbkdf2_hmac(
                "sha256", self.password.encode("utf-8"), salt, 100000
            )

        salt = os.urandom(32)
        key = hashlib.pbkdf2_hmac("sha256", self.password.encode("utf-8"), salt, 100000)
        player.details.map["s:password"] = [
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
        after_add = self.area.add_item(self.item)
        world.register(after_add)

        # We do this after because we may consolidate this Item and
        # this keeps us from having to unregister the item.
        world.register(after_add)

        await world.bus.publish(ItemsAppeared(area=self.area, items=[self.item]))
        await ctx.extend(area=self.area, appeared=[self.item]).hook("appeared:after")
        return Success("%s appeared" % (p.join([self.item]),))


class Make(PersonAction):
    def __init__(self, template=None, item=None, **kwargs):
        super().__init__(**kwargs)
        self.item = None
        self.template = None
        self.template = template
        self.item = item

    async def perform(self, ctx: Ctx, world: World, player: Player):
        item = self.item
        if self.template:
            item = self.template.create_item(person=player, creator=player)
            assert isinstance(item, things.Item)
        after_hold = player.hold(item)
        # We do this after because we may consolidate this Item and
        # this keeps us from having to unregister the item.
        world.register(after_hold)
        area = world.find_player_area(player)
        await world.bus.publish(ItemsMade(person=player, area=area, items=[after_hold]))
        return Success("you're now holding %s" % (after_hold,), item=after_hold)


class Hug(PersonAction):
    def __init__(self, who=None, **kwargs):
        super().__init__(**kwargs)
        self.who = who

    async def perform(self, ctx: Ctx, world: World, player: Player):
        if not self.who:
            return Failure("who?")
        await ctx.extend(hug=self.who).hook("hug:after")
        return Success("you hugged %s" % (self.who))


class Heal(PersonAction):
    def __init__(self, who=None, **kwargs):
        super().__init__(**kwargs)
        self.who = who

    async def perform(self, ctx: Ctx, world: World, player: Player):
        if not self.who:
            return Failure("who?")
        await ctx.extend(heal=self.who).hook("heal:after")
        return Success("you healed %s" % (self.who))


class Kiss(PersonAction):
    def __init__(self, who=None, **kwargs):
        super().__init__(**kwargs)
        self.who = who

    async def perform(self, ctx: Ctx, world: World, player: Player):
        if not self.who:
            return Failure("who?")
        await ctx.extend(kiss=self.who).hook("kiss:after")
        return Success("you kissed %s" % (self.who))


class Tickle(PersonAction):
    def __init__(self, who=None, **kwargs):
        super().__init__(**kwargs)
        self.who = who

    async def perform(self, ctx: Ctx, world: World, player: Player):
        if not self.who:
            return Failure("who?")
        await ctx.extend(tickle=self.who).hook("tickle:after")
        return Success("you tickled %s" % (self.who))


class Poke(PersonAction):
    def __init__(self, who=None, **kwargs):
        super().__init__(**kwargs)
        self.who = who

    async def perform(self, ctx: Ctx, world: World, player: Player):
        if not self.who:
            return Failure("who?")
        # TODO Publish
        await ctx.extend(poke=self.who).hook("poke:after")
        return Success("you poked %s" % (self.who))


class Hit(PersonAction):
    def __init__(self, item: things.ItemFinder = None, **kwargs):
        super().__init__(**kwargs)
        assert item
        self.item = item

    async def perform(self, ctx: Ctx, world: World, player: Player):
        item = world.apply_item_finder(player, self.item)
        if not item:
            return Failure("hit what?")
        await ctx.extend(swing=item).hook("hit")
        return Success("you hit %s" % (item))


class Kick(PersonAction):
    def __init__(self, item: things.ItemFinder = None, **kwargs):
        super().__init__(**kwargs)
        assert item
        self.item = item

    async def perform(self, ctx: Ctx, world: World, player: Player):
        item = world.apply_item_finder(player, self.item)
        if not item:
            return Failure("what?")
        await ctx.extend(kick=item).hook("kick:after")
        return Success("you kicked %s" % (item))


class Plant(PersonAction):
    def __init__(self, item: things.ItemFinder = None, **kwargs):
        super().__init__(**kwargs)
        assert item
        self.item = item

    async def perform(self, ctx: Ctx, world: World, player: Player):
        if not self.item:
            return Failure("plant what?")
        await ctx.extend(plant=self.item).hook("plant")
        return Success("you planted %s" % (self.item))


class Shake(PersonAction):
    def __init__(self, item: things.ItemFinder = None, **kwargs):
        super().__init__(**kwargs)
        assert item
        self.item = item

    async def perform(self, ctx: Ctx, world: World, player: Player):
        item = world.apply_item_finder(player, self.item)
        if not item:
            return Failure("shake what?")
        await ctx.extend(shake=item).hook("shake")
        return Success("you shook %s" % (item))


class Swing(PersonAction):
    def __init__(self, item: things.ItemFinder = None, **kwargs):
        super().__init__(**kwargs)
        assert item
        self.item = item

    async def perform(self, ctx: Ctx, world: World, player: Player):
        item = world.apply_item_finder(player, self.item)
        if self.item:
            return Failure("swing what?")
        await ctx.extend(swing=item).hook("swing")
        return Success("you swung %s" % (item))


class Wear(PersonAction):
    def __init__(self, item: things.ItemFinder = None, **kwargs):
        super().__init__(**kwargs)
        assert item
        self.item = item

    async def perform(self, ctx: Ctx, world: World, player: Player):
        item = world.apply_item_finder(player, self.item)
        if not item:
            return Failure("wear what?")

        if not item.when_worn():
            return Failure("you can't wear that")

        assert player.is_holding(item)

        if player.wear(item):
            player.drop(item)

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

        if not player.is_wearing(item):
            return Failure("you aren't wearing that")

        assert player.is_wearing(item)

        if player.unwear(item):
            player.hold(item)

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

        if not item.when_eaten():
            return Failure("you can't eat that")

        area = world.find_player_area(player)
        await player.consume(item, area=area, ctx=ctx)
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

        if not item.when_drank():
            return Failure("you can't drink that")

        area = world.find_player_area(player)
        await player.consume(item, area=area, ctx=ctx)
        await ctx.extend(eat=item).hook("drink:after")

        return Success("you drank %s" % (item))


class Join(PersonAction):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def perform(self, ctx: Ctx, world: World, player: Player):
        world.register(player)
        await world.bus.publish(PlayerJoined(player=player))
        await ctx.hook("entered:before")
        await world.welcome_area().entered(world.bus, player)
        await ctx.hook("entered:after")
        return Success("welcome!")


class LookFor(PersonAction):
    def __init__(self, name: str = None, **kwargs):
        super().__init__(**kwargs)
        self.name = name

    async def perform(self, ctx: Ctx, world: World, player: Player):
        area = world.find_player_area(player)
        await ctx.extend(holding=player.holding).extend(name=self.name).hook("look-for")
        return PersonalObservation(player)


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
        return EntitiesObservation(things.expected(player.holding))


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
        dropped, failure = player.drop_here(
            area, item, quantity=self.quantity, creator=player, ctx=ctx
        )
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

        if player.is_holding(item):
            return Failure("you're already holding that")

        area = world.find_player_area(player)
        if self.quantity:
            removed = item.separate(self.quantity, creator=player, ctx=ctx)
            if item.quantity == 0:
                world.unregister(item)
                area.drop(item)
            item = removed[0]
        else:
            area.unhold(item)

        after_hold = player.hold(item)
        if after_hold != item:
            world.unregister(item)
        await world.bus.publish(ItemHeld(person=player, area=area, hold=[after_hold]))
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

        if not item.open():
            return Failure("you can't open that")

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

        if not item.close():
            return Failure("you can't close that")

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
        locked_with = item.lock(key=maybe_key, creator=player, **kwargs)
        if not locked_with:
            return Failure("can't seem to lock that")

        player.hold(locked_with)

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
        if item.unlock(key=maybe_key, **kwargs):
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

        item = world.apply_item_finder(player, self.item)
        if not item:
            return Failure("what?")

        if container.place_inside(item):
            player.drop(item)

        return Success("inside, done")


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

        item = world.apply_item_finder(player, self.item)
        if not item:
            return Failure("what?")

        if container.take_out(item):
            player.hold(item)
        else:
            return Failure("doesn't seem like you can")

        return Success("inside, done")


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
            log.info("finder: %s", self.finder)
            area = world.find_player_area(player)
            route = await self.finder.find_route(area, player, verb=verb, builder=world)
            if route:
                routed: Any = route.area
                destination = routed

        if destination is None:
            return Failure("where?")

        await ctx.extend(area=area).hook("left:before")
        await area.left(world.bus, player)
        await ctx.extend(area=area).hook("left:after")

        await ctx.extend(area=destination).hook("entered:before")
        await destination.entered(world.bus, player)
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
        items = player.drop_all()
        if len(items) == 0:
            return Failure("you're not holding anything")

        item: Any = None  # TODO CarryableMixin to Entity
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

        # Copy all of the base details from the item. Exclude stamps.
        template = item
        recipe = Recipe(
            creator=player,
            details=item.details.clone(),
            behaviors=item.behaviors,
            kind=item.kind,
            template=template,
        )
        world.register(recipe)
        player.memory["r:" + self.name] = recipe
        return Success(
            "cool, you'll be able to make another %s easier now" % (self.name,)
        )


class Forget(PersonAction):
    def __init__(self, name=None, **kwargs):
        super().__init__(**kwargs)
        self.name = name

    async def perform(self, ctx: Ctx, world: World, player: Player):
        if self.name in player.memory:
            del player.memory[self.name]
            return Success("oh wait, was that important?")
        return Failure("huh, seems i already have forgotten that!")


class Remember(PersonAction):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def perform(self, ctx: Ctx, world: World, player: Player):
        area = world.find_player_area(player)
        player.memory[MemoryAreaKey] = area
        return Success("you'll be able to remember this place, oh yeah")


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

        if self.field in health.NutritionFields:
            item.nutrition.properties[self.field] = self.value
        else:
            item.details.set(self.field, self.value)
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

        item.link_activity(self.activity, self.value)
        item.details.set(self.activity, self.value)
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
        item.servings = self.number
        return Success("done")


class ItemsAppeared(Event):
    pass
