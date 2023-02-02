
from os.path import basename
name = basename(__file__)[:-2]

# ---------------------> Logging setup

import logging
log = logging.getLogger(name)

# ---------------------> Example cog

from discord.ext import commands

def setup(bot: commands.Bot) -> None:
    bot.add_cog(Example(bot))
    log.info(f'Extension has been created: {name}')

def teardown(bot: commands.Bot) -> None:
    log.info(f'Extension has been destroyed: {name}')

class Example(commands.Cog, name = name, description = 'An example extension'):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
    
    @commands.command()
    async def ping(self, ctx) -> None:
        await ctx.channel.send('Pong!')
