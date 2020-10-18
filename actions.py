import os
import hashlib
import base64

from game import *
from props import *
import hooks

MemoryAreaKey = "m:area"
log = logging.getLogger("dimsum")


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

        await world.bus.publish(ItemsAppeared(self.area, [self.item]))
        await ctx.extend(area=self.area, appeared=[self.item]).hook("appeared:after")
        return Success("%s appeared" % (p.join([self.item]),))


class ItemsAppeared(Event):
    def __init__(self, area: Area, items: Sequence[Item]):
        self.area = area
        self.items = items

    def __str__(self):
        return "%s appeared" % (p.join(self.items),)


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
            item = self.template.apply_item_template(creator=player)
        after_hold = player.hold(item)
        # We do this after because we may consolidate this Item and
        # this keeps us from having to unregister the item.
        world.register(after_hold)
        area = world.find_player_area(player)
        await world.bus.publish(ItemMade(player, area, after_hold))
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


class Kick(PersonAction):
    def __init__(self, who=None, **kwargs):
        super().__init__(**kwargs)
        self.who = who

    async def perform(self, ctx: Ctx, world: World, player: Player):
        if not self.who:
            return Failure("who?")
        await ctx.extend(kick=self.who).hook("kick:after")
        return Success("you kicked %s" % (self.who))


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


class Plant(PersonAction):
    def __init__(self, item=None, **kwargs):
        super().__init__(**kwargs)
        self.item = item

    async def perform(self, ctx: Ctx, world: World, player: Player):
        if not self.item:
            return Failure("plant what?")
        # TODO Publish
        await ctx.extend(plant=self.item).hook("plant")
        return Success("you planted %s" % (self.item))


class Shake(PersonAction):
    def __init__(self, item=None, **kwargs):
        super().__init__(**kwargs)
        self.item = item

    async def perform(self, ctx: Ctx, world: World, player: Player):
        if not self.item:
            return Failure("shake what?")
        # TODO Publish
        await ctx.extend(shake=self.item).hook("shake")
        return Success("you shook %s" % (self.item))


class Hit(PersonAction):
    def __init__(self, item=None, **kwargs):
        super().__init__(**kwargs)
        self.item = item

    async def perform(self, ctx: Ctx, world: World, player: Player):
        if not self.item:
            return Failure("hit what?")
        # TODO Publish
        await ctx.extend(swing=self.item).hook("hit")
        return Success("you hit %s" % (self.item))


class Swing(PersonAction):
    def __init__(self, item=None, **kwargs):
        super().__init__(**kwargs)
        self.item = item

    async def perform(self, ctx: Ctx, world: World, player: Player):
        if not self.item:
            return Failure("swing what?")
        # TODO Publish
        await ctx.extend(swing=self.item).hook("swing")
        return Success("you swung %s" % (self.item))


class Wear(PersonAction):
    def __init__(self, item=None, **kwargs):
        super().__init__(**kwargs)
        self.item = item

    async def perform(self, ctx: Ctx, world: World, player: Player):
        if not self.item:
            return Failure("wear what?")

        if not self.item.details.when_worn():
            return Failure("you can't wear that")

        player.wear(self.item)
        # TODO Publish
        await ctx.extend(wear=[self.item]).hook("wear:after")
        return Success("you wore %s" % (self.item))


class Remove(PersonAction):
    def __init__(self, item=None, **kwargs):
        super().__init__(**kwargs)
        self.item = item

    async def perform(self, ctx: Ctx, world: World, player: Player):
        if not self.item:
            return Failure("remove what?")
        if not player.is_wearing(self.item):
            return Failure("you aren't wearing that")
        player.remove(self.item)
        await ctx.extend(remove=[self.item]).hook("remove:after")
        return Success("you removed %s" % (self.item))


class Eat(PersonAction):
    def __init__(self, item=None, **kwargs):
        super().__init__(**kwargs)
        self.item = item

    async def perform(self, ctx: Ctx, world: World, player: Player):
        if not self.item:
            return Failure("dunno where that is")

        if not self.item.details.when_eaten():
            return Failure("you can't eat that")

        area = world.find_player_area(player)
        world.unregister(self.item)
        player.drop(self.item)
        player.consume(self.item)
        await world.bus.publish(ItemEaten(player, area, self.item))
        await ctx.extend(eat=self.item).hook("eat:after")
        return Success("you ate %s" % (self.item))


class Drink(PersonAction):
    def __init__(self, item=None, **kwargs):
        super().__init__(**kwargs)
        self.item = item

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


class Drop(PersonAction):
    def __init__(self, item=None, quantity=None, **kwargs):
        super().__init__(**kwargs)
        self.quantity = quantity if quantity else None
        self.item = item if item else None

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

            dropped = self.item.separate(world, player, self.quantity)
            if self.item.quantity == 0:
                world.unregister(self.item)
                player.drop(self.item)
        else:
            if self.item:
                dropped = player.drop(self.item)
            else:
                dropped = player.drop_all()

        for item in dropped:
            after_add = area.add_item(item)
            if after_add != item:
                world.unregister(item)

        await world.bus.publish(ItemsDropped(player, area, dropped))
        await ctx.extend(dropped=dropped).hook("drop:after")
        return Success("you dropped %s" % (p.join(dropped),))


class Join(PersonAction):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def perform(self, ctx: Ctx, world: World, player: Player):
        world.register(player)
        await world.bus.publish(PlayerJoined(player))
        await ctx.hook("entered:before")
        await world.welcome_area().entered(world.bus, player)
        await ctx.hook("entered:after")
        return Success("welcome!")


class LookFor(PersonAction):
    def __init__(self, name=None, **kwargs):
        super().__init__(**kwargs)
        self.name = name

    async def perform(self, ctx: Ctx, world: World, player: Player):
        area = world.find_player_area(player)
        await ctx.extend(here=area.here).extend(holding=player.holding).extend(
            name=self.name
        ).hook("look-for")
        observed = player.observe()[0]
        return PersonalObservation(observed)


class LookMyself(PersonAction):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def perform(self, ctx: Ctx, world: World, player: Player):
        await ctx.hook("look-myself")
        observed = player.observe()[0]
        return PersonalObservation(observed)


class LookDown(PersonAction):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def perform(self, ctx: Ctx, world: World, player: Player):
        await ctx.hook("look-down")
        return EntitiesObservation(player.holding)


class Look(PersonAction):
    def __init__(self, item=None, **kwargs):
        super().__init__(**kwargs)
        self.item = item

    async def perform(self, ctx: Ctx, world: World, player: Player):
        if self.item:
            observed = player.observe()
            if len(observed) == 0:
                raise Exception("invisible observation")
            return DetailedObservation(observed[0], ObservedEntity(self.item))
        return world.look(player)


class Hold(PersonAction):
    def __init__(self, item=None, **kwargs):
        super().__init__(**kwargs)
        self.item = item

    async def perform(self, ctx: Ctx, world: World, player: Player):
        if not self.item:
            return Failure("sorry, hold what?")

        area = world.find_player_area(player)

        if player.is_holding(self.item):
            return Failure("you're already holding that")

        area.remove(self.item)
        after_hold = player.hold(self.item)
        if after_hold != self.item:
            world.unregister(self.item)
        await world.bus.publish(ItemHeld(player, area, after_hold))
        await ctx.extend(hold=[after_hold]).hook("hold:after")
        return Success("you picked up %s" % (after_hold,), item=after_hold)


class MovingAction(PersonAction):
    def __init__(self, area=None, item=None, **kwargs):
        super().__init__(**kwargs)
        self.area = area
        self.item = item

    async def move(self, verb: str, ctx: Ctx, world: World, player: Player):
        area = world.find_player_area(player)

        destination = self.area

        # If the person owns this item and they try to go the thing,
        # this is how new areas area created, one of them.
        if self.item:
            log.info("verb check: %s" % (verb,))
            if verb not in self.item.areas:
                new_area = world.build_new_area(player, area, self.item)
                self.item.link_area(new_area, verb=verb)
            destination = self.item.areas[verb]

            # TODO Only drop the door!
            await world.perform(player, Drop())

        if not destination:
            return Failure("where?")

        await ctx.extend(area=area).hook("left:before")
        await area.left(world.bus, player)
        await ctx.extend(area=area).hook("left:after")

        await ctx.extend(area=destination).hook("entered:before")
        await destination.entered(world.bus, player)
        await ctx.extend(area=destination).hook("entered:after")

        return world.look(player)


class Climb(MovingAction):
    async def perform(self, ctx: Ctx, world: World, player: Player):
        # If climb ever becomes a string outside of this function, rethink.
        await ctx.extend().hook("climb:before")
        return await self.move("climb", ctx, world, player)


class Go(MovingAction):
    async def perform(self, ctx: Ctx, world: World, player: Player):
        await ctx.extend().hook("walk:before")
        return await self.move(DefaultMoveVerb, ctx, world, player)


class Obliterate(PersonAction):
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


class CallThis(PersonAction):
    def __init__(self, name=None, item=None, **kwargs):
        super().__init__(**kwargs)
        self.item = item
        self.name = name

    async def perform(self, ctx: Ctx, world: World, player: Player):
        if not self.item:
            return Failure("you don't have anything")

        # Copy all of the base details from the item. Exclude stamps.
        base = self.item.details.to_base()
        if "created" in base:
            del base["created"]
        if "touched" in base:
            del base["touched"]

        recipe = Recipe(
            creator=player,
            details=self.item.details.clone(),
            behaviors=self.item.behaviors,
            kind=self.item.kind,
            base=base,
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
        self.item.details.set(self.field, self.value)
        return Success("done")


class ModifyActivity(PersonAction):
    def __init__(self, item=None, activity=None, value=None, **kwargs):
        super().__init__(**kwargs)
        self.item = item
        self.activity = activity
        self.value = value

    async def perform(self, ctx: Ctx, world: World, player: Player):
        if not self.item:
            return Failure("nothing to modify")
        self.item.link_activity(self.activity, self.value)
        self.item.details.set(self.activity, self.value)
        return Success("done")


class Tick(Action):
    def __init__(self, time=None, **kwargs):
        self.time = time

    async def perform(self, ctx: Ctx, world: World, player: Player):
        return None
