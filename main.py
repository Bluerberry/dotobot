import logging
from logging import config

from os import getenv
from dotenv import load_dotenv
load_dotenv()

import discord
from discord.ext import commands

# ---------------------> Logging setup

config.fileConfig('log.conf')
log = logging.getLogger('root')

# ---------------------> Bot setup

intents = discord.Intents.all()
bot = commands.Bot(command_prefix = '$', intents = intents)

@bot.event
async def on_ready():
    log.info(f'Succesful login as {bot.user}')

# ---------------------> Main

if __name__ == '__main__':

    from cogs.example_cog import Example # TODO anything but this
    bot.add_cog(Example(bot))
    bot.run(getenv('DISCORD_TOKEN'))