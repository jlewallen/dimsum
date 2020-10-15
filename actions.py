import os
import hashlib
import base64

from game import *
from props import *


class Unknown(Action):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def perform(self, ctx: Ctx, world: World, player: Player):
        return Failure("sorry, i don't understand")


class Auth(Action):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.password = kwargs["password"]

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
        return Success("done, https://url")


class Plant(Action):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.item = kwargs["item"]

    async def perform(self, ctx: Ctx, world: World, player: Player):
        pass


class Home(Action):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def perform(self, ctx: Ctx, world: World, player: Player):
        await ctx.extend().hook("home:before")
        return await Go(area=world.welcome_area()).perform(ctx, world, player)


class Make(Action):
    def __init__(self, item, **kwargs):
        super().__init__(**kwargs)
        self.item = item

    async def perform(self, ctx: Ctx, world: World, player: Player):
        if not self.item:
            return Failure("todo: fix")
        area = world.find_player_area(player)
        player.hold(self.item)
        world.register(self.item)
        await world.bus.publish(ItemMade(player, area, self.item))
        return Success("you're now holding a %s" % (self.item,))


class Hug(Action):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.who = kwargs["who"]

    async def perform(self, ctx: Ctx, world: World, player: Player):
        if self.who:
            return Success("you hugged %s" % (self.who))
        await ctx.extend(hug=self.who).hook("hug:after")
        return Failure("who?")


class Heal(Action):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.who = kwargs["who"]

    async def perform(self, ctx: Ctx, world: World, player: Player):
        if self.who:
            return Success("you healed %s" % (self.who))
        await ctx.extend(heal=self.who).hook("heal:after")
        return Failure("who?")


class Kick(Action):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.who = kwargs["who"]

    async def perform(self, ctx: Ctx, world: World, player: Player):
        if self.who:
            return Success("you kicked %s" % (self.who))
        await ctx.extend(kick=self.who).hook("kick:after")
        return Failure("who?")


class Kiss(Action):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.who = kwargs["who"]

    async def perform(self, ctx: Ctx, world: World, player: Player):
        if self.who:
            return Success("you kissed %s" % (self.who))
        await ctx.extend(kiss=self.who).hook("kiss:after")
        return Failure("who?")


class Tickle(Action):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.who = kwargs["who"]

    async def perform(self, ctx: Ctx, world: World, player: Player):
        if self.who:
            return Success("you tickled %s" % (self.who))
        await ctx.extend(tickle=self.who).hook("tickle:after")
        return Failure("who?")


class Poke(Action):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.who = kwargs["who"]

    async def perform(self, ctx: Ctx, world: World, player: Player):
        if self.who:
            return Success("you poked %s" % (self.who))
        await ctx.extend(poke=self.who).hook("poke:after")
        return Failure("who?")


class Eat(Action):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.item = kwargs["item"]

    async def perform(self, ctx: Ctx, world: World, player: Player):
        if not self.item.details.when_eaten():
            return Failure("you can't eat that")

        area = world.find_player_area(player)
        world.unregister(self.item)
        player.drop(self.item)
        player.consume(self.item)
        await world.bus.publish(ItemEaten(player, area, self.item))
        await ctx.extend(eat=self.item).hook("eat:after")
        return Failure("you ate %s" % (self.item))


class Drink(Action):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.item = kwargs["item"]

    async def perform(self, ctx: Ctx, world: World, player: Player):
        if not self.item:
            return Failure("dunno where that is")
        if not self.item.details.when_drank():
            return Failure("you can't drink that")

        area = world.find_player_area(player)
        world.unregister(self.item)
        player.drop(self.item)
        player.consume(self.item)
        await world.bus.publish(ItemDrank(player, area, self.item))
        await ctx.extend(drink=self.item).hook("drink:after")
        return Success("you drank %s" % (self.item))


class Drop(Action):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def perform(self, ctx: Ctx, world: World, player: Player):
        area = world.find_player_area(player)
        dropped = await area.drop(world.bus, player)
        if len(dropped) == 0:
            return Failure("nothing to drop")
        await ctx.extend(dropped=dropped).hook("drop:after")
        return Success("you dropped %s" % (p.join(dropped),))


class Join(Action):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def perform(self, ctx: Ctx, world: World, player: Player):
        world.register(player)
        await world.bus.publish(PlayerJoined(player))
        await world.welcome_area().entered(world.bus, player)
        return Success("welcome!")


class Myself(Action):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def perform(self, ctx: Ctx, world: World, player: Player):
        return PersonalObservation(player.observe())


class Look(Action):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.item = kwargs["item"] if "item" in kwargs else None

    async def perform(self, ctx: Ctx, world: World, player: Player):
        if self.item:
            return DetailedObservation(player.observe(), self.item)
        return world.look(player)


class Hold(Action):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.item = kwargs["item"]

    async def perform(self, ctx: Ctx, world: World, player: Player):
        if not self.item:
            return Failure("sorry, hold what?")

        area = world.find_player_area(player)

        if player.is_holding(self.item):
            return Failure("you're already holding that")

        if self.item.area and self.item.owner != player:
            return Failure("that's not yours")

        area.remove(self.item)
        player.hold(self.item)
        await world.bus.publish(ItemHeld(player, area, self.item))

        await ctx.extend(hold=[self.item]).hook("hold:after")

        return Success("you picked up %s" % (self.item,))


class Go(Action):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.area = kwargs["area"] if "area" in kwargs else None
        self.item = kwargs["item"] if "item" in kwargs else None

    async def perform(self, ctx: Ctx, world: World, player: Player):
        area = world.find_player_area(player)

        destination = self.area

        # If the person owns this item and they try to go the thing,
        # this is how new areas area created, one of them.
        if self.item:
            if self.item.area is None:
                if self.item.owner != player:
                    return Failure("you can only do that with things you own")
                self.item.area = world.build_new_area(player, area, self.item)
            destination = self.item.area

        await world.perform(player, Drop())
        await area.left(world.bus, player)
        await destination.entered(world.bus, player)


class Obliterate(Action):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def perform(self, ctx: Ctx, world: World, player: Player):
        area = world.find_player_area(player)
        items = player.drop_all()
        if len(items) == 0:
            return Failure("you're not holding anything")

        for item in items:
            world.unregister(item)
            await world.bus.publish(ItemObliterated(player, area, item))

        await ctx.extend(obliterate=items).hook("obliterate:after")

        return Success("you obliterated %s" % (p.join(list(map(str, items))),))


class CallThis(Action):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.item = kwargs["item"]
        self.name = kwargs["name"]

    async def perform(self, ctx: Ctx, world: World, player: Player):
        if not self.item:
            return Failure("you don't have anything")

        base = self.item.details.to_base()

        if "created" in base:
            del base["created"]
        if "touched" in base:
            del base["touched"]

        recipe = Recipe(
            owner=player,
            details=props.Details(self.name),
            base=base,
        )
        world.register(recipe)
        player.memory["r:" + self.name] = recipe
        return Success(
            "cool, you'll be able to make another %s easier now" % (self.name,)
        )


class Forget(Action):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = kwargs["name"]

    async def perform(self, ctx: Ctx, world: World, player: Player):
        if self.name in player.memory:
            del player.memory[self.name]
            return Success("oh wait, was that important?")
        return Failure("huh, seems i already have forgotten that!")


class Remember(Action):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def perform(self, ctx: Ctx, world: World, player: Player):
        area = world.find_player_area(player)
        player.memory[MemoryAreaKey] = area
        return Success("you'll be able to remember this place, oh yeah")


class ModifyField(Action):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.item = kwargs["item"]
        self.field = kwargs["field"]
        self.value = kwargs["value"]

    async def perform(self, ctx: Ctx, world: World, player: Player):
        self.item.details.set(self.field, self.value)
        return Success("done")


class ModifyActivity(Action):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.item = kwargs["item"]
        self.activity = kwargs["activity"]
        self.value = kwargs["value"]

    async def perform(self, ctx: Ctx, world: World, player: Player):
        if not self.item:
            return Failure("nothing to modify")
        self.item.details.set(self.activity, self.value)
        return Success("done")
