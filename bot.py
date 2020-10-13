import discord
import discord.ext.commands
import logging
import inflect
import game
import lark
import persistence
import grammar
import evaluator

p = inflect.engine()


class DiscordEventBus(game.EventBus):
    def __init__(self, bot):
        self.bot = bot

    async def publish(self, event: game.Event):
        logging.info("publish:%s", event)
        for channel in self.bot.get_all_channels():
            if channel.name == "IGNORED":
                await channel.send(str(event))


class BotPlayer:
    def __init__(self, player, channel):
        self.player = player
        self.channel = channel


class EmbedObservation:
    def personal(self, obs):
        emd = obs.details.desc
        emd += "\n"
        for key, value in obs.properties.items():
            emd += "\n" + key + "=" + str(value)
        return emd

    def detailed(self, obs):
        emd = obs.details.desc
        emd += "\n"
        for key, value in obs.properties.items():
            emd += "\n" + key + "=" + str(value)
        return emd

    def area(self, obs):
        emd = obs.details.desc
        emd += "\n\n"
        if len(obs.people) > 0:
            emd += "Also here: " + p.join([str(x) for x in obs.people])
            emd += "\n"
        if len(obs.items) > 0:
            emd += "You can see " + p.join([str(x) for x in obs.items])
            emd += "\n"
        if len(obs.who.holding) > 0:
            emd += "You're holding " + p.join([str(x) for x in obs.who.holding])
            emd += "\n"
        return emd


async def mutate(reply, mutation):
    try:
        await mutation()
    except game.SorryError as err:
        await reply(str(err))
    except game.AlreadyHolding as err:
        await reply(str(err))
    except game.NotHoldingAnything as err:
        await reply(str(err))
    except game.HoldingTooMuch as err:
        await reply(str(err))
    except game.UnknownField as err:
        await reply(str(err))
    except game.NotYours as err:
        await reply(str(err))
    except game.YouCantDoThat as err:
        await reply(str(err))
    except lark.exceptions.VisitError as err:
        await reply("oops, %s" % (err.__context__,))
    except Exception as err:
        await reply("oops, %s" % (err,))


class GameBot:
    def parse_as(self, evaluator, prefix, remaining):
        tree = self.l.parse(prefix + " " + remaining)
        return evaluator.transform(tree)

    def __init__(self, token):
        bot = discord.ext.commands.Bot(".")

        self.baseUrl = "http://192.168.0.100:5000"
        self.token = token
        self.bot = bot
        self.players = {}
        self.world = None
        self.l = grammar.create_parser()

        @bot.event
        async def on_ready():
            self.world = await self.initialize()
            print(f"{bot.user} has connected")

        @bot.command(
            name="look",
            brief="Look around.",
            description="Look around.",
            pass_context=True,
            aliases=["l", "where", "here"],
        )
        async def look(ctx, *, q: str = ""):
            player = await self.get_player(ctx.message)
            action = self.parse_as(evaluator.create(self.world, player), "look", q)
            observation = await self.world.perform(player, action)
            visitor = EmbedObservation()
            emd = observation.accept(visitor)
            em = discord.Embed(title=observation.details.name, description=emd)
            await ctx.message.channel.send(embed=em)

        @bot.command(
            name="home",
            brief="Home! Quick! Save me!",
            description="Home! Quick! Save me!",
            pass_context=True,
            aliases=[],
        )
        async def home(ctx, *, q: str = ""):
            async def op():
                player = await self.get_player(ctx.message)
                action = self.parse_as(evaluator.create(self.world, player), "home", q)
                await self.world.perform(player, action)
                await self.save()
                await ctx.message.channel.send("there ya go")

            await mutate(ctx.message.channel.send, op)

        @bot.command(
            name="hold",
            brief="Pick something up off the ground, or from a place that's visible.",
            description="Pick something up off the ground, or from a place that's visible.",
            pass_context=True,
            aliases=["h", "take", "get"],
        )
        async def hold(ctx, *, q: str):
            async def op():
                player = await self.get_player(ctx.message)
                action = self.parse_as(evaluator.create(self.world, player), "hold", q)
                held = await self.world.perform(player, action)
                if len(held) == 0:
                    await ctx.message.channel.send("you can't hold that")
                    return

                await ctx.message.channel.send("you picked up %s" % (p.join(held),))
                await self.save()

            await mutate(ctx.message.channel.send, op)

        @bot.command(
            name="drop",
            brief="Drop everything in your hands.",
            description="Drop everything in your hands.",
            pass_context=True,
            aliases=["d"],
        )
        async def drop(ctx, *, q: str = ""):
            async def op():
                player = await self.get_player(ctx.message)
                action = self.parse_as(evaluator.create(self.world, player), "drop", q)
                dropped = await self.world.perform(player, action)
                if len(dropped) == 0:
                    await ctx.message.channel.send("nothing to drop")
                    return

                await ctx.message.channel.send("you dropped %s" % (p.join(dropped),))
                await self.save()

            await mutate(ctx.message.channel.send, op)

        @bot.command(
            name="remember",
            brief="Remember a place, useful for finding your way back.",
            description="Remember a place, useful for finding your way back.",
            pass_context=True,
            aliases=[],
        )
        async def remember(ctx, *, q: str = ""):
            async def op():
                player = await self.get_player(ctx.message)
                await self.world.perform(player, game.Remember())

                await ctx.message.channel.send(
                    "you'll be able to remember this place, oh yeah"
                )
                await self.save()

            await mutate(ctx.message.channel.send, op)

        @bot.command(
            name="make",
            brief="Make a new item.",
            description="Make a new item.",
            pass_context=True,
            aliases=[],
        )
        async def make(ctx, *, q: str):
            async def op():
                player = await self.get_player(ctx.message)
                action = self.parse_as(evaluator.create(self.world, player), "make", q)
                item = await self.world.perform(player, action)
                await self.save()

                await ctx.message.channel.send("you're now holding %s" % (item,))

            await mutate(ctx.message.channel.send, op)

        @bot.command(
            name="modify",
            brief="Modify attributes/properties of items that are being held.",
            description="""
Modify attributes/properties of items that are being held.

modify [name|desc|presence] <TEXT>
modify [capacity|size|weight|nutrition|toxicity] <NUMBER>
modify when opened
modify when eaten
""",
            pass_context=True,
            aliases=[],
        )
        async def modify(ctx, *, q: str):
            async def op():
                player = await self.get_player(ctx.message)
                action = self.parse_as(
                    evaluator.create(self.world, player), "modify", q
                )
                await self.world.perform(player, action)
                await self.save()
                await ctx.message.channel.send("done")

            await mutate(ctx.message.channel.send, op)

        @bot.command(
            name="eat",
            brief="Eat something.",
            description="Eat something.",
            pass_context=True,
            aliases=[],
        )
        async def eat(ctx, *, q: str):
            async def op():
                player = await self.get_player(ctx.message)
                action = self.parse_as(evaluator.create(self.world, player), "eat", q)
                item = await self.world.perform(player, action)
                await self.save()

                await ctx.message.channel.send("you ate %s" % (item,))

            await mutate(ctx.message.channel.send, op)

        @bot.command(
            name="drink",
            brief="Drink something.",
            description="Drink something.",
            pass_context=True,
            aliases=[],
        )
        async def drink(ctx, *, q: str):
            async def op():
                player = await self.get_player(ctx.message)
                action = self.parse_as(evaluator.create(self.world, player), "drink", q)
                item = await self.world.perform(player, action)
                await self.save()

                await ctx.message.channel.send("you drank %s" % (item,))

            await mutate(ctx.message.channel.send, op)

        @bot.command(
            name="obliterate",
            brief="Destroy items being held forever",
            description="Any items the player is holding are reduced to an uptick of warmth in the server room, never to be seen again",
            pass_context=True,
            aliases=[],
        )
        async def obliterate(ctx):
            async def op():
                player = await self.get_player(ctx.message)
                await self.world.perform(player, game.Obliterate())
                await self.save()

            await mutate(ctx.message.channel.send, op)

        @bot.command(
            name="go",
            brief="Move around the world, just say where.",
            description="Move around the world, just say where.",
            pass_context=True,
        )
        async def go(ctx, *, q: str):
            async def op():
                player = await self.get_player(ctx.message)
                action = self.parse_as(evaluator.create(self.world, player), "go", q)
                await self.world.perform(player, action)
                await self.save()
                await look(ctx)

            await mutate(ctx.message.channel.send, op)

    def run(self):
        self.bot.run(self.token)

    def stop(self):
        self.bot.logout()

    async def initialize(self):
        self.bus = DiscordEventBus(self.bot)
        self.world = game.World(self.bus)

        db = persistence.SqlitePersistence()
        await db.open("world.sqlite3")
        await db.load(self.world)

        if self.world.empty():
            self.world.add_area(
                game.Area(
                    owner=world, details=game.Details("Living room", "It's got walls.")
                ).add_item(
                    game.Item(
                        owner=world, details=game.Details("Hammer", "It's heavy.")
                    )
                )
            )

        return self.world

    async def save(self):
        db = persistence.SqlitePersistence()
        await db.open("world.sqlite3")
        await db.save(self.world)

    async def get_player(self, message):
        author = message.author
        channel = message.channel
        key = str(author.id)

        if key in self.players:
            self.players[key].channel = channel
            return self.players[key].player

        if self.world.contains(key):
            player = self.world.find(key)
            self.players[key] = BotPlayer(player, channel)
            return player

        player = game.Player(
            key=key,
            owner=self.world,
            details=game.Details(author.name, "A discord user"),
        )
        self.players[key] = BotPlayer(player, channel)
        await self.world.perform(player, game.Join())
        await self.save()
        return player
