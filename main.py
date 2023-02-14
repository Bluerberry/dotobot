
import logging
from logging import config
from os import getenv

import discord
from discord.ext import commands
from dotenv import load_dotenv

import util
from entities import db

# ---------------------> Logging setup

config.fileConfig('log.conf')
log = logging.getLogger('root')

# ---------------------> Environment setup

load_dotenv()

# ---------------------> Configure database

db.bind(provider='postgres', user=getenv('DB_USER'), password=getenv('DB_PASSWORD'),
        host=getenv('DB_HOST'), port=getenv('DB_PORT'), database=getenv('DB_NAME'))
db.generate_mapping(check_tables=True, create_tables=True)

# ---------------------> Discord setup

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='$', intents=intents)

@bot.event
async def on_ready() -> None:
    log.info(f'Succesful login as {bot.user}')

# ---------------------> Main

if __name__ == '__main__':
    for ext in util.yield_extensions(prefix_path=True):
        try:
            bot.load_extension(ext)
        except Exception as err:
            log.error(err)
        
    bot.run(getenv('DISCORD_TOKEN'))