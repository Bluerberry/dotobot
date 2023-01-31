import logging
from logging import config

from os import getenv, listdir
from dotenv import load_dotenv
load_dotenv()

import discord
from discord.ext import commands
from discord import ExtensionAlreadyLoaded

# ---------------------> Logging setup

config.fileConfig('log.conf')
log = logging.getLogger('root')

# ---------------------> Bot setup

intents = discord.Intents.all()
bot = commands.Bot(command_prefix = '$', intents = intents)

@bot.event
async def on_ready() -> None:
    log.info(f'Succesful login as {bot.user}')      

# ---------------------> Main

if __name__ == '__main__':
    for ext in ['cogs.' + file[:-3] for file in listdir('./cogs') if file.endswith('.py')]:
        try:
            bot.load_extension(ext)
        except ExtensionAlreadyLoaded as err:
            log.warning(err)
        except Exception as err:
            log.error(err)
        
    bot.run(getenv('DISCORD_TOKEN'))