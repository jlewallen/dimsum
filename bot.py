import discord
import discord.ext.commands
import logging
import game
import persistence

bot = discord.ext.commands.Bot(".")


players = {}
world = None


class DiscordEventBus(game.EventBus):
    def __init__(self, bot):
        self.bot = bot

    async def publish(self, event: game.Event):
        logging.info("publish:%s", event)
        for channel in self.bot.get_all_channels():
            if channel.name == "test":
                await channel.send(str(event))


class BotPlayer:
    def __init__(self, player, channel):
        self.player = player
        self.channel = channel


def get_world():
    return world


async def initialize_world():
    bus = DiscordEventBus(bot)
    world = game.World(bus)

    db = persistence.SqlitePersistence()
    await db.open("world.sqlite3")
    await db.load(world)

    if world.empty():
        world.add_area(
            game.Area(
                owner=world, details=game.Details("Living room", "It's got walls.")
            ).add_item(
                game.Item(owner=world, details=game.Details("Hammer", "It's heavy."))
            )
        )

    return world


async def save_world():
    db = persistence.SqlitePersistence()
    await db.open("world.sqlite3")
    await db.save(world)


async def get_player(message):
    author = message.author
    channel = message.channel
    key = str(author.id)

    if key in players:
        players[key].channel = channel
        return players[key].player

    if world.contains(key):
        player = world.find(key)
        players[key] = BotPlayer(player, channel)
        return player

    player = game.Player(
        key=key, owner=world, details=game.Details(author.name, "A discord user")
    )
    players[key] = BotPlayer(player, channel)
    await world.join(player)
    await save_world()
    return player


async def mutate(reply, mutation):
    try:
        await mutation()
    except game.SorryError:
        await reply("sorry")
    except game.AlreadyHolding:
        await reply("you're already holding that")
    except game.NotHoldingAnything:
        await reply("you need to be holding something for that")
    except game.HoldingTooMuch:
        await reply("you're holding too much")
    except game.UnknownField:
        await reply("i dunno how to change that")


@bot.event
async def on_ready():
    global world
    world = await initialize_world()
    print(f"{bot.user} has connected")


@bot.command(
    name="ping",
    description="ping",
    brief="ping",
    pass_context=True,
)
async def ping(ctx):
    await ctx.message.channel.send("pong")


@bot.command(
    name="look",
    description="look",
    brief="look",
    pass_context=True,
    aliases=["where", "here"],
)
async def look(ctx):
    player = await get_player(ctx.message)
    observation = world.look(player)
    await ctx.message.channel.send(str(observation))


@bot.command(
    name="hold",
    description="hold",
    brief="hold",
    pass_context=True,
    aliases=["take", "get"],
)
async def hold(ctx, *, q: str = ""):
    async def op():
        player = await get_player(ctx.message)
        held = await world.hold(player, q)
        if len(held) == 0:
            await ctx.message.channel.send("you can't hold that")
        else:
            await save_world()

    await mutate(ctx.message.channel.send, op)


@bot.command(
    name="drop",
    description="drop",
    brief="drop",
    pass_context=True,
)
async def drop(ctx):
    async def op():
        player = await get_player(ctx.message)
        dropped = await world.drop(player)
        if len(dropped) == 0:
            await ctx.message.channel.send("nothing to drop")
        else:
            await save_world()

    await mutate(ctx.message.channel.send, op)


@bot.command(
    name="make",
    description="make",
    brief="make",
    pass_context=True,
    aliases=[],
)
async def make(ctx, *, name: str):
    async def op():
        player = await get_player(ctx.message)
        item = game.Item(owner=player, details=game.Details(name, name))
        await world.make(player, item)
        await save_world()

    await mutate(ctx.message.channel.send, op)


@bot.command(
    name="modify",
    description="modify",
    brief="modify",
    pass_context=True,
    aliases=[],
)
async def modify(ctx, *, changeQ: str):
    async def op():
        player = await get_player(ctx.message)
        await world.modify(player, changeQ)
        await save_world()

    await mutate(ctx.message.channel.send, op)


@bot.command(
    name="go",
    description="go",
    brief="go",
    pass_context=True,
)
async def go(ctx, *, where: str = ""):
    async def op():
        player = await get_player(ctx.message)
        await world.go(player, where)
        await save_world()

    await mutate(ctx.message.channel.send, op)


class GameBot:
    def __init__(self, token):
        global bot
        self.bot = bot
        self.token = token

    def run(self):
        self.bot.run(self.token)

    def stop(self):
        self.bot.logout()
