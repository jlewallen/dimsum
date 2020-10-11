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


async def initialize_world():
    bus = DiscordEventBus(bot)
    world = game.World(bus)

    db = persistence.SqlitePersistence()
    await db.open("world.sqlite3")
    await db.load(world)
    if world.empty():
        await world.add_area(
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
    if author.id in players:
        players[author.id].channel = channel
        return players[author.id].player

    if world.contains(author.id):
        player = world.find(author.id)
        players[author.id] = BotPlayer(player, channel)
        return player

    player = game.Player(
        key=author.id, owner=world, details=game.Details(author.name, "A discord user")
    )
    players[author.id] = BotPlayer(player, channel)
    await world.join(player)
    return player


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
    name="hold",
    description="hold",
    brief="hold",
    pass_context=True,
    aliases=["take", "get"],
)
async def hold(ctx, *, q: str = ""):
    player = await get_player(ctx.message)
    held = await world.hold(player, q)
    if len(held) == 0:
        await ctx.message.channel.send("you can't hold that")
    else:
        await save_world()


@bot.command(
    name="drop",
    description="drop",
    brief="drop",
    pass_context=True,
)
async def drop(ctx):
    player = await get_player(ctx.message)
    dropped = await world.drop(player)
    if len(dropped) == 0:
        await ctx.message.channel.send("nothing to drop")
    await save_world()


@bot.command(
    name="go",
    description="go",
    brief="go",
    pass_context=True,
)
async def go(ctx):
    pass


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
    name="make",
    description="make",
    brief="make",
    pass_context=True,
    aliases=[],
)
async def make(ctx, *, name: str):
    player = await get_player(ctx.message)
    item = game.Item(owner=player, details=game.Details(name, name))
    await world.make(player, item)
    await save_world()


@bot.command(
    name="build",
    description="build",
    brief="build",
    pass_context=True,
    aliases=[],
)
async def build(ctx, *, name: str):
    player = await get_player(ctx.message)
    item = game.Item(owner=player, details=game.Details(name, name))
    await world.build(player, item)
    await save_world()


@bot.command(
    name="modify",
    description="modify",
    brief="modify",
    pass_context=True,
    aliases=[],
)
async def modify(ctx, *, q: str, how: str):
    player = await get_player(ctx.message)
    logging.info(q, how)


class GameBot:
    def __init__(self, token):
        global bot
        self.bot = bot
        self.token = token

    def run(self):
        self.bot.run(self.token)

    def stop(self):
        self.bot.logout()
