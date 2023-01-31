
# Logging setup
import logging
from logging import config

config.fileConfig('log.conf')
logger = logging.getLogger('root')

# Environment setup
import os
from dotenv import load_dotenv
load_dotenv()

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