
from util import yield_extensions

# ---------------------> Logging setup

import logging
from logging import config

config.fileConfig('log.conf')
log = logging.getLogger('root')

# ---------------------> Environment setup

from os import getenv
from dotenv import load_dotenv

load_dotenv()

# ---------------------> Configure database

from entities import db

db.bind(provider='postgres', user=getenv('DB_USER'), password=getenv('DB_PASSWORD'),
        host=getenv('DB_HOST'), port=getenv('DB_PORT'), database=getenv('DB_NAME'))
db.generate_mapping(check_tables=True, create_tables=True)

# ---------------------> Discord setup

import discord
from discord.ext import commands

intents = discord.Intents.all()
bot = commands.Bot(command_prefix = '$', intents = intents)

@bot.event
async def on_ready() -> None:
    log.info(f'Succesful login as {bot.user}')

# ---------------------> Main

if __name__ == '__main__':
    for ext in yield_extensions('extensions', import_path = True):
        try:
            bot.load_extension(ext)
        except Exception as err:
            log.error(err)
        
    bot.run(getenv('DISCORD_TOKEN'))