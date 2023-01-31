import logging
from logging import config

from discord.ext import commands

# ---------------------> Logging setup

log = logging.getLogger('example')

# ---------------------> Example cog

class Example(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot
        log.info('Succesful cog bootup')
    
    @commands.command()
    async def ping(self, ctx) -> None:
        await ctx.channel.send('Pong!')
        log.info(f'{ctx.author} played a match of pingpong!')
