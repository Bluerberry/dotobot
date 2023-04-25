
import logging
from logging import config
from os import getenv

import discord
from discord.ext import commands
from dotenv import load_dotenv
from pony.orm import db_session

import util
from entities import User, db

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
    
    # Add all members from all guilds to database
    with db_session:
        for guild in bot.guilds:
            for member in guild.members:
                if bot.application_id == member.id:
                    continue

                if User.exists(discord_id=member.id):
                    log.debug(f"New user `{member.name}` ({member.id}) already known")
                    continue

                User(discord_id=member.id)
                log.info(f'New user `{member.name}` ({member.id}) added to the database')
    
    log.info(f'Succesful login as {bot.user}')

@bot.event
async def on_member_join(member: discord.User) -> None:

    # Find greet chanel
    channel = bot.get_channel(int(getenv('GREET_CHANNEL_ID')))
    if channel == None:
        log.error(f'Failed to load greet channel ({getenv("GREET_CHANNEL_ID")})')
        return

    # Check if new user is already known
    with db_session:
        if User.exists(discord_id=member.id):
            log.debug(f"New user `{member.name}` ({member.id}) already known")
            return
        
        User(discord_id=member.id)
        log.info(f'New user `{member.name}` ({member.id}) added to the database')
    
    # Send greetings
    await channel.send(f'Welcome {member.mention}, to {channel.guild.name}!')

# ---------------------> Main

if __name__ == '__main__':

    # Load all extensions
    for ext in util.yield_extensions(prefix_path=True):
        try:
            bot.load_extension(ext)
        except Exception as err:
            log.error(err)
    
    bot.run(getenv('DISCORD_TOKEN'))