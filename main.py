
import json
import logging
import logging.config
import os

import discord
import dotenv
import pony.orm as pony
from discord.ext import commands

import lib.entities as entities
import lib.util as util


# ---------------------> Setup


# Logging
log = logging.getLogger('main')
with open('logConfig.json') as file:
    logging.config.dictConfig(json.load(file))

# Environment variables
dotenv.load_dotenv()

# Database
entities.db.bind(provider='postgres', user=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD'),
        host=os.getenv('DB_HOST'), port=os.getenv('DB_PORT'), database=os.getenv('DB_NAME'))
entities.db.generate_mapping(check_tables=True, create_tables=True)

# Discord bot
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='$', intents=intents)


# ---------------------> Main


if __name__ == '__main__':

    # Load all extensions
    with pony.db_session:
        for ext in util.yield_extensions(prefix_path=True):
            try:

                # Skip extensions marked inactive
                name = util.extension_name(ext)
                if entities.Extension.exists(name=name):
                    extension = entities.Extension.get(name=name)
                    if not extension.active:
                        log.warning(f'Skipped loading inactive extension `{name}`')
                        continue

                # Load extension
                bot.load_extension(ext)

            except Exception as err:
                log.error(err)

    bot.run(os.getenv('DISCORD_TOKEN'))