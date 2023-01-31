
# Logging setup
import logging
from logging import config

config.fileConfig('log.conf')
logger = logging.getLogger('root')

# Environment setup
import os
from dotenv import load_dotenv

load_dotenv()

# configure database
from entities import db

db.bind(provider='postgres', user=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD'),
        host=os.getenv('DB_HOST'), port=os.getenv('DB_PORT'), database=os.getenv('DB_NAME'))
db.generate_mapping(check_tables=True, create_tables=True)


# Discord setup
import discord

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents = intents)

@client.event
async def on_ready():
    logger.info(f'Succesful login as {client.user}')

@client.event
async def on_message(msg):
    if msg.content == 'ping':
        await msg.channel.send('pong')
        logger.info(f'{msg.author} played a match of ping-pong!')

client.run(os.getenv('DISCORD_TOKEN'))