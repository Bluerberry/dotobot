from util import extract_flags

import logging
from logging import config

from os import getenv, listdir
from dotenv import load_dotenv

load_dotenv()

# Configure database
from entities import db

db.bind(provider='postgres', user=getenv('DB_USER'), password=getenv('DB_PASSWORD'),
        host=getenv('DB_HOST'), port=getenv('DB_PORT'), database=getenv('DB_NAME'))
db.generate_mapping(check_tables=True, create_tables=True)

# Discord setup
import discord
from discord.ext import commands
from discord import ExtensionAlreadyLoaded, ExtensionNotLoaded, ExtensionNotFound

# ---------------------> Logging setup

config.fileConfig('log.conf')
log = logging.getLogger('root')

# ---------------------> Bot setup

intents = discord.Intents.all()
bot = commands.Bot(command_prefix = '$', intents = intents)

@bot.event
async def on_ready() -> None:
    log.info(f'Succesful login as {bot.user}')

@bot.command(name='load')
@extract_flags
async def load(ctx: commands.Context, flags, params) -> None:

    # Preperations
    total: int = 0
    success: int = 0
    summary: str = ''

    if not params or 'all' in flags:
        params = [file[:-3] for file in listdir('./extensions') if file.endswith('.py')]

    # Load extensions
    for ext in params:

        try:
            bot.load_extension('extensions.' + ext)
            summary += f'🟢 {ext} sucessfully loaded\n'

        except ExtensionAlreadyLoaded as err:
            log.warning(err)
            summary += f'🟡 {ext} was already loaded\n'

        except ExtensionNotFound as err:
            log.warning(err)
            summary += f'🟠 {ext} doesn\'t exist\n'

        except Exception as err:
            log.error(err)
            summary += f'🔴 {ext} failed to load\n'
        
        else:
            success += 1
        finally:
            total += 1
    
    # TODO Maybe use discord pages for a nicer interface
    # Feedback
    if 'silent' not in flags:
        if total == 0:
            await ctx.channel.send(f'No extensions have loaded')
            return
        if 'verbose' in flags:
            await ctx.channel.send(f'```{summary}```')
        if success == total:
            await ctx.channel.send(f'All extensions have loaded')
        else:
            await ctx.channel.send(f'{success} out of {total} extensions have loaded')

@bot.command(name='unload')
@extract_flags
async def unload(ctx: commands.Context, flags, params) -> None:

    # Preperations
    total: int = 0
    success: int = 0
    summary: str = ''

    if not params or 'all' in flags:
        params = [ext[11:] for ext in bot.extensions.keys()]

    # Unload extensions
    for ext in params:

        try:
            bot.unload_extension('extensions.' + ext)
            summary += f'🟢 {ext} sucessfully unloaded\n'

        except ExtensionNotLoaded as err:
            log.warning(err)
            summary += f'🟡 {ext} was already unloaded\n'

        except ExtensionNotFound as err:
            log.warning(err)
            summary += f'🟠 {ext} doesn\'t exist\n'

        except Exception as err:
            log.error(err)
            summary += f'🔴 {ext} failed to unload\n'
        
        else:
            success += 1
        finally:
            total += 1
    
    # TODO Maybe use discord pages for a nicer interface
    # Feedback
    if 'silent' not in flags:
        if total == 0:
            await ctx.channel.send(f'No extensions have unloaded')
            return
        if 'verbose' in flags:
            await ctx.channel.send(f'```{summary}```')
        if success == total:
            await ctx.channel.send(f'All extensions have unloaded')
        else:
            await ctx.channel.send(f'{success} out of {total} extensions have unloaded')

@bot.command(name='reload')
@extract_flags
async def reload(ctx: commands.Context, flags, params) -> None:

    # Preperations
    total: int = 0
    success: int = 0
    summary: str = ''

    if not params or 'all' in flags:
        params = [ext[11:] for ext in bot.extensions.keys()]

    # Reload extensions
    for ext in params:

        try:
            bot.reload_extension('extensions.' + ext)
            summary += f'🟢 {ext} sucessfully reloaded\n'

        except ExtensionNotLoaded as err:
            log.warning(err)
            summary += f'🟡 {ext} wasn\'t loaded\n'

        except ExtensionNotFound as err:
            log.warning(err)
            summary += f'🟠 {ext} doesn\'t exist\n'

        except Exception as err:
            log.error(err)
            summary += f'🔴 {ext} failed to reload\n'
        
        else:
            success += 1
        finally:
            total += 1
    
    # TODO Maybe use discord pages for a nicer interface
    # Feedback
    if 'silent' not in flags:
        if total == 0:
            await ctx.channel.send(f'No extensions have reloaded')
            return
        if 'verbose' in flags:
            await ctx.channel.send(f'```{summary}```')
        if success == total:
            await ctx.channel.send(f'All extensions have reloaded')
        else:
            await ctx.channel.send(f'{success} out of {total} extensions have reloaded')


# ---------------------> Main

if __name__ == '__main__':
    for ext in ['extensions.' + file[:-3] for file in listdir('./extensions') if file.endswith('.py')]:
        try:
            bot.load_extension(ext)
        except ExtensionAlreadyLoaded as err:
            log.warning(err)
        except Exception as err:
            log.error(err)
        
    bot.run(getenv('DISCORD_TOKEN'))