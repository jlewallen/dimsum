import discord
import discord.ext.commands

bot = discord.ext.commands.Bot(".")


@bot.event
async def on_ready():
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
    name="where",
    description="where",
    brief="where",
    pass_context=True,
)
async def where(ctx):
    user_id = ctx.message.author.id
    name = ctx.message.author.display_name
    await ctx.message.channel.send("indeed, %s (%d)!" % (name, user_id))


@bot.command(
    name="take",
    description="take",
    brief="take",
    pass_context=True,
)
async def take(ctx):
    user_id = ctx.message.author.id
    name = ctx.message.author.display_name
    await ctx.message.channel.send("indeed, %s (%d)!" % (name, user_id))


@bot.command(
    name="drop",
    description="drop",
    brief="drop",
    pass_context=True,
)
async def drop(ctx):
    user_id = ctx.message.author.id
    name = ctx.message.author.display_name
    await ctx.message.channel.send("indeed, %s (%d)!" % (name, user_id))


@bot.command(
    name="go",
    description="go",
    brief="go",
    pass_context=True,
)
async def go(ctx):
    user_id = ctx.message.author.id
    name = ctx.message.author.display_name
    await ctx.message.channel.send("indeed, %s (%d)!" % (name, user_id))


@bot.command(
    name="look",
    description="look",
    brief="look",
    pass_context=True,
)
async def look(ctx):
    user_id = ctx.message.author.id
    name = ctx.message.author.display_name
    await ctx.message.channel.send("indeed, %s (%d)!" % (name, user_id))


class GameBot:
    def __init__(self, token):
        global bot
        self.bot = bot
        self.token = token

    def run(self):
        self.bot.run(self.token)

    def stop(self):
        self.bot.logout()
