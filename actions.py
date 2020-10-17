import os
import hashlib
import base64

from game import *
from props import *
import hooks


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
        return Success("done, https://mud.espial.me")


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
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.item = None
        self.template = None
        if "template" in kwargs:
            self.template = kwargs["template"]
        if "item" in kwargs:
            self.item = kwargs["item"]

    async def perform(self, ctx: Ctx, world: World, player: Player):
        item = self.item
        if self.template:
            item = self.template.apply_item_template(owner=player)
        world.register(item)
        player.hold(item)
        area = world.find_player_area(player)
        await world.bus.publish(ItemMade(player, area, item))
        return Success("you're now holding %s" % (item,))


class Hug(Action):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.who = kwargs["who"]

    async def perform(self, ctx: Ctx, world: World, player: Player):
        if not self.who:
            return Failure("who?")
        await ctx.extend(hug=self.who).hook("hug:after")
        return Success("you hugged %s" % (self.who))


class Heal(Action):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.who = kwargs["who"]

    async def perform(self, ctx: Ctx, world: World, player: Player):
        if not self.who:
            return Failure("who?")
        await ctx.extend(heal=self.who).hook("heal:after")
        return Success("you healed %s" % (self.who))


class Kick(Action):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.who = kwargs["who"]

    async def perform(self, ctx: Ctx, world: World, player: Player):
        if not self.who:
            return Failure("who?")
        await ctx.extend(kick=self.who).hook("kick:after")
        return Success("you kicked %s" % (self.who))


class Kiss(Action):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.who = kwargs["who"]

    async def perform(self, ctx: Ctx, world: World, player: Player):
        if not self.who:
            return Failure("who?")
        await ctx.extend(kiss=self.who).hook("kiss:after")
        return Success("you kissed %s" % (self.who))


class Tickle(Action):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.who = kwargs["who"]

    async def perform(self, ctx: Ctx, world: World, player: Player):
        if not self.who:
            return Failure("who?")
        await ctx.extend(tickle=self.who).hook("tickle:after")
        return Success("you tickled %s" % (self.who))


class Poke(Action):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.who = kwargs["who"]

    async def perform(self, ctx: Ctx, world: World, player: Player):
        if not self.who:
            return Failure("who?")
        await ctx.extend(poke=self.who).hook("poke:after")
        return Success("you poked %s" % (self.who))


class Plant(Action):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.item = kwargs["item"]

    async def perform(self, ctx: Ctx, world: World, player: Player):
        if not self.item:
            return Failure("plant what?")
        await ctx.extend(plant=self.item).hook("plant")
        return Success("you poked %s" % (self.who))


class Shake(Action):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.item = kwargs["item"]

    async def perform(self, ctx: Ctx, world: World, player: Player):
        if not self.item:
            return Failure("shake what?")
        await ctx.extend(shake=self.item).hook("shake")
        return Success("you shook %s" % (self.item))


class Hit(Action):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.item = kwargs["item"]

    async def perform(self, ctx: Ctx, world: World, player: Player):
        if not self.item:
            return Failure("hit what?")
        await ctx.extend(swing=self.item).hook("hit")
        return Success("you hit %s" % (self.item))


class Swing(Action):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.item = kwargs["item"]

    async def perform(self, ctx: Ctx, world: World, player: Player):
        if not self.item:
            return Failure("swing what?")
        await ctx.extend(swing=self.item).hook("swing")
        return Success("you swung %s" % (self.item))


class Wear(Action):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.item = kwargs["item"]

    async def perform(self, ctx: Ctx, world: World, player: Player):
        if not self.item:
            return Failure("wear what?")
        player.wear(self.item)
        await ctx.extend(wear=self.item).hook("wear:after")
        return Success("you wore %s" % (self.item))


class Remove(Action):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.item = kwargs["item"]

    async def perform(self, ctx: Ctx, world: World, player: Player):
        if not self.item:
            return Failure("remove what?")
        player.remove(self.item)
        await ctx.extend(remove=self.item).hook("remove:after")
        return Success("you removed %s" % (self.item))


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
        self.quantity = None
        if "quantity" in kwargs:
            self.quantity = kwargs["quantity"]
        self.item = None
        if "item" in kwargs:
            self.item = kwargs["item"]

    async def perform(self, ctx: Ctx, world: World, player: Player):
        if len(player.holding) == 0:
            return Failure("nothing to drop")

        area = world.find_player_area(player)
        dropped = []
        if self.quantity:
            if not self.item:
                return Failure("please specify what?")

            if self.quantity > self.item.quantity or self.quantity < 1:
                return Failure("you should check how many you have")

            dropped = self.item.separate(player, self.quantity)

            if self.item.quantity == 0:
                world.unregister(self.item)
                player.drop(self.item)
        else:
            dropped = player.drop_all()

        for item in dropped:
            area.here.append(item)
            await world.bus.publish(ItemDropped(player, self, item))
        await ctx.extend(dropped=dropped).hook("drop:after")
        return Success("you dropped %s" % (p.join(dropped),))


class Join(Action):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def perform(self, ctx: Ctx, world: World, player: Player):
        world.register(player)
        await world.bus.publish(PlayerJoined(player))
        await ctx.hook("entered:before")
        await world.welcome_area().entered(world.bus, player)
        await ctx.hook("entered:after")
        return Success("welcome!")


class LookFor(Action):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = kwargs["name"] if "name" in kwargs else None

    async def perform(self, ctx: Ctx, world: World, player: Player):
        await ctx.extend(holding=player.holding).extend(name=self.name).hook("look-for")
        return PersonalObservation(player.observe())


class LookMyself(Action):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def perform(self, ctx: Ctx, world: World, player: Player):
        await ctx.hook("look-myself")
        return PersonalObservation(player.observe())


class LookDown(Action):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def perform(self, ctx: Ctx, world: World, player: Player):
        await ctx.hook("look-down")
        return EntitiesObservation(player.holding)


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

        area.remove(self.item)
        player.hold(self.item)
        await world.bus.publish(ItemHeld(player, area, self.item))

        await ctx.extend(hold=[self.item]).hook("hold:after")

        return Success("you picked up %s" % (self.item,))


class MovingAction(Action):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.area = kwargs["area"] if "area" in kwargs else None
        self.item = kwargs["item"] if "item" in kwargs else None

    async def move(self, verb: str, ctx: Ctx, world: World, player: Player):
        area = world.find_player_area(player)

        destination = self.area

        # If the person owns this item and they try to go the thing,
        # this is how new areas area created, one of them.
        if self.item:
            if verb not in self.item.areas:
                if self.item.owner != player:
                    return Failure("you can only do that with things you own")
                new_area = world.build_new_area(player, area, self.item)
                self.item.areas[verb] = new_area
            destination = self.item.areas[verb]

        await world.perform(player, Drop())

        await ctx.extend(area=area).hook("left:before")
        await area.left(world.bus, player)
        await ctx.extend(area=area).hook("left:after")

        await ctx.extend(area=destination).hook("entered:before")
        await destination.entered(world.bus, player)
        await ctx.extend(area=destination).hook("entered:after")

        return world.look(player)


class Climb(MovingAction):
    async def perform(self, ctx: Ctx, world: World, player: Player):
        await ctx.extend().hook("climb:before")
        return await self.move("climb", ctx, world, player)


class Go(MovingAction):
    async def perform(self, ctx: Ctx, world: World, player: Player):
        await ctx.extend().hook("walk:before")
        return await self.move("walk", ctx, world, player)


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
