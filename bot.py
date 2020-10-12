import discord
import discord.ext.commands
import logging
import game
import persistence
import inflect

bot = discord.ext.commands.Bot(".")


baseUrl = "http://192.168.0.100:5000/"
players = {}
world = None


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
    except game.NotYours:
        await reply("that's not yours, sorry")


@bot.event
async def on_ready():
    global world
    world = await initialize_world()
    print(f"{bot.user} has connected")


@bot.command(
    name="look",
    description="Look around.",
    brief="Look around.",
    pass_context=True,
    aliases=["where", "here"],
)
async def look(ctx):
    player = await get_player(ctx.message)
    observation = world.look(player)

    p = inflect.engine()

    emd = observation.details.desc
    emd += "\n\n"
    if len(observation.people) > 0:
        emd += "Also here: " + p.join([str(x) for x in observation.people])
        emd += "\n"
    if len(observation.items) > 0:
        emd += "You can see " + p.join([str(x) for x in observation.items])
        emd += "\n"
    if len(observation.who.holding) > 0:
        emd += "You're holding " + p.join([str(x) for x in observation.who.holding])
        emd += "\n"

    em = discord.Embed(title=observation.details.name, description=emd)

    await ctx.message.channel.send(embed=em)


@bot.command(
    name="hold",
    description="Pick something up off the ground, or from a place that's visible.",
    brief="Pick something up off the ground, or from a place that's visible.",
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
    description="Drop everything in your hands.",
    brief="Drop everything in your hands.",
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
    name="inspect",
    description="Inspect things closer.",
    brief="Inspect things closer.",
    pass_context=True,
    aliases=[],
)
async def inspect(ctx):
    player = await get_player(ctx.message)
    if len(player.holding) == 0:
        await ctx.message.channel.send("try holding something")
        return

    em = discord.Embed(title="Inspection", colour=0x00FF00)
    for item in player.holding:
        em.add_field(name=str(item), value="[open](%s%s)" % (baseUrl, item.key))
    await ctx.message.channel.send(embed=em)


@bot.command(
    name="make",
    description="Make a new item.",
    brief="Make a new item.",
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
    description="Modify attributes/properties of items that are being held",
    brief="Modify attributes/properties of items that are being held",
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
    name="obliterate",
    description="Any items the player is holding are reduced to an uptick of warmth in the server room, never to be seen again",
    brief="Destroy items being held forever",
    pass_context=True,
    aliases=[],
)
async def modify(ctx):
    async def op():
        player = await get_player(ctx.message)
        await world.obliterate(player)
        await save_world()

    await mutate(ctx.message.channel.send, op)


@bot.command(
    name="go",
    description="Move around the world, just say where.",
    brief="Move around the world, just say where.",
    pass_context=True,
)
async def go(ctx, *, where: str = ""):
    async def op():
        player = await get_player(ctx.message)
        await world.go(player, where)
        await save_world()
        await look(ctx)

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
