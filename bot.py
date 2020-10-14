import discord
import discord.ext.commands
import logging
import inflect
import props
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


class EmbedObservationVisitor:
    def personal(self, obs):
        emd = obs.details.desc
        emd += "\n"

        emd += "Properties:\n"
        for key, value in obs.properties.items():
            emd += key + "=" + str(value) + "\n"
        emd += "\n"

        emd += "Memory:\n"
        for key, value in obs.memory.items():
            emd += key + "=" + str(value) + "\n"
        emd += "\n"

        return {"embed": discord.Embed(title=obs.details.name, description=emd)}

    def detailed(self, obs):
        emd = obs.details.desc
        emd += "\n"
        for key, value in obs.properties.items():
            emd += "\n" + key + "=" + str(value)
        return {"embed": discord.Embed(title=obs.details.name, description=emd)}

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
        return {"embed": discord.Embed(title=obs.details.name, description=emd)}


class ReplyVisitor(EmbedObservationVisitor):
    def failure(self, reply):
        return {"content": reply.message}

    def success(self, reply):
        return {"content": reply.message}


class GameBot:
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
            return await self.repl(ctx, "look", q)

        @bot.command(
            name="home",
            brief="Home! Quick! Save me!",
            description="Home! Quick! Save me!",
            pass_context=True,
            aliases=[],
        )
        async def home(ctx, *, q: str = ""):
            return await self.repl(ctx, "home", q)

        @bot.command(
            name="m",
            brief="Command!",
            description="Command!",
            pass_context=True,
        )
        async def generic(ctx, *, q: str):
            return await self.repl(ctx, q)

        @bot.command(
            name="hold",
            brief="Pick something up off the ground, or from a place that's visible.",
            description="Pick something up off the ground, or from a place that's visible.",
            pass_context=True,
            aliases=["h", "take", "get"],
        )
        async def hold(ctx, *, q: str):
            return await self.repl(ctx, "hold", q)

        @bot.command(
            name="drop",
            brief="Drop everything in your hands.",
            description="Drop everything in your hands.",
            pass_context=True,
            aliases=["d"],
        )
        async def drop(ctx, *, q: str = ""):
            return await self.repl(ctx, "drop", q)

        @bot.command(
            name="remember",
            brief="Remember a place, useful for finding your way back.",
            description="Remember a place, useful for finding your way back.",
            pass_context=True,
            aliases=[],
        )
        async def remember(ctx, *, q: str = ""):
            return await self.repl(ctx, "remember", q)

        @bot.command(
            name="make",
            brief="Make a new item.",
            description="Make a new item.",
            pass_context=True,
            aliases=[],
        )
        async def make(ctx, *, q: str):
            return await self.repl(ctx, "make", q)

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
            return await self.repl(ctx, "modify", q)

        @bot.command(
            name="eat",
            brief="Eat something.",
            description="Eat something.",
            pass_context=True,
            aliases=[],
        )
        async def eat(ctx, *, q: str):
            return await self.repl(ctx, "eat", q)

        @bot.command(
            name="drink",
            brief="Drink something.",
            description="Drink something.",
            pass_context=True,
            aliases=[],
        )
        async def drink(ctx, *, q: str):
            return await self.repl(ctx, "drink", q)

        @bot.command(
            name="obliterate",
            brief="Destroy items being held forever",
            description="Any items the player is holding are reduced to an uptick of warmth in the server room, never to be seen again",
            pass_context=True,
            aliases=[],
        )
        async def obliterate(ctx, *, q: str = ""):
            return await self.repl(ctx, "obliterate", q)

        @bot.command(
            name="go",
            brief="Move around the world, just say where.",
            description="Move around the world, just say where.",
            pass_context=True,
        )
        async def go(ctx, *, q: str):
            return await self.repl(ctx, "go", q)

        @bot.command(
            name="hug",
            brief="Hug",
            description="Hug",
            pass_context=True,
        )
        async def hug(ctx, *, q: str):
            return await self.repl(ctx, "hug", q)

        @bot.command(
            name="heal",
            brief="Heal",
            description="Heal",
            pass_context=True,
        )
        async def heal(ctx, *, q: str):
            return await self.repl(ctx, "heal", q)

        @bot.command(
            name="kick",
            brief="Kick",
            description="Kick",
            pass_context=True,
        )
        async def kick(ctx, *, q: str):
            return await self.repl(ctx, "kick", q)

        @bot.command(
            name="kiss",
            brief="Kiss",
            description="Kiss",
            pass_context=True,
        )
        async def kiss(ctx, *, q: str):
            return await self.repl(ctx, "kiss", q)

        @bot.command(
            name="tickle",
            brief="Tickle",
            description="Tickle",
            pass_context=True,
        )
        async def tickle(ctx, *, q: str):
            return await self.repl(ctx, "tickle", q)

        @bot.command(
            name="poke",
            brief="Poke",
            description="Poke",
            pass_context=True,
        )
        async def poke(ctx, *, q: str):
            return await self.repl(ctx, "poke", q)

    def parse_as(self, evaluator, prefix, remaining=""):
        full = prefix + " " + remaining
        tree = self.l.parse(full.strip())
        logging.info(str(tree))
        return evaluator.transform(tree)

    async def send(self, ctx, reply):
        visitor = ReplyVisitor()
        visual = reply.accept(visitor)
        print(reply, visual)
        if visual:
            await ctx.message.channel.send(**visual)

    async def repl(self, ctx, full_command: str, q: str = ""):
        async def op():
            player = await self.get_player(ctx.message)
            action = self.parse_as(
                evaluator.create(self.world, player), full_command, q
            )
            reply = await self.world.perform(player, action)
            await self.save()
            return reply

        reply = await self.translate(op)
        await self.send(ctx, reply)

    async def translate(self, mutation):
        try:
            return await mutation()
        except Exception as err:
            logging.error("error", exc_info=True)
            return game.Failure("oops, %s" % (err,))

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
                    owner=self.world,
                    details=props.Details("Living room", desc="It's got walls."),
                ).add_item(
                    game.Item(
                        owner=self.world,
                        details=props.Details("Hammer", desc="It's heavy."),
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

        if not self.world:
            raise ExceptioException("initializing")

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
            details=props.Details(author.name, desc="A discord user"),
        )
        self.players[key] = BotPlayer(player, channel)
        await self.world.perform(player, actions.Join())
        await self.save()
        return player
