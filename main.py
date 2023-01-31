import logging
from logging import config

from os import getenv, listdir
from dotenv import load_dotenv
load_dotenv()

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

@bot.command()
async def load(ctx: commands.Context, *args) -> None:
    
    # Flags
    all: bool = '--all' in args
    silent: bool = '--silent' in args
    verbose: bool = '--verbose' in args

    # Preperations
    total: int = 0
    success: int = 0
    summary: str = ''

    if not args or all:
        args = ['extensions.' + file[:-3] for file in listdir('./extensions') if file.endswith('.py')]
    else:
        args = ['extensions.' + arg for arg in args if not arg.startswith('--')]

    # Load extensions
    for arg in args:

        try:
            bot.load_extension(arg)
            summary += f'🟢 {arg} sucessfully loaded\n'

        except ExtensionAlreadyLoaded as err:
            log.warning(err)
            summary += f'🟡 {arg} was already loaded\n'

        except ExtensionNotFound as err:
            log.warning(err)
            summary += f'🟠 {arg} doesn\'t exist\n'

        except Exception as err:
            log.error(err)
            summary += f'🔴 {arg} failed to load\n'
        
        else:
            success += 1
        finally:
            total += 1
    
    # TODO Maybe use discord pages for a nicer interface
    # Feedback
    if not silent:
        if total == 0:
            await ctx.channel.send(f'No extensions have loaded')
            return
        if verbose:
            await ctx.channel.send(f'```{summary}```')
        if success == total:
            await ctx.channel.send(f'All extensions have loaded')
        else:
            await ctx.channel.send(f'{success} out of {total} extensions have loaded')

@bot.command()
async def unload(ctx: commands.Context, *args) -> None:
   
    # Flags
    all: bool = '--all' in args
    silent: bool = '--silent' in args
    verbose: bool = '--verbose' in args

    # Preperations
    total: int = 0
    success: int = 0
    summary: str = ''

    if not args or all:
        args = list(bot.extensions.keys())
    else:
        args = ['extensions.' + arg for arg in args if not arg.startswith('--')]

    # Unload extensions
    for arg in args:

        try:
            bot.unload_extension(arg)
            summary += f'🟢 {arg} sucessfully unloaded\n'

        except ExtensionNotLoaded as err:
            log.warning(err)
            summary += f'🟡 {arg} was already unloaded\n'

        except ExtensionNotFound as err:
            log.warning(err)
            summary += f'🟠 {arg} doesn\'t exist\n'

        except Exception as err:
            log.error(err)
            summary += f'🔴 {arg} failed to unload\n'
        
        else:
            success += 1
        finally:
            total += 1
    
    # TODO Maybe use discord pages for a nicer interface
    # Feedback
    if not silent:
        if total == 0:
            await ctx.channel.send(f'No extensions have unloaded')
            return
        if verbose:
            await ctx.channel.send(f'```{summary}```')
        if success == total:
            await ctx.channel.send(f'All extensions have unloaded')
        else:
            await ctx.channel.send(f'{success} out of {total} extensions have unloaded')

@bot.command()
async def reload(ctx: commands.Context, *args) -> None:
      
    # Flags
    all: bool = '--all' in args
    silent: bool = '--silent' in args
    verbose: bool = '--verbose' in args

    # Preperations
    total: int = 0
    success: int = 0
    summary: str = ''

    if all:
        args = list(bot.extensions.keys())
    else:
        args = ['extensions.' + arg for arg in args if not arg.startswith('--')]

    # Reload extensions
    for arg in args:

        try:
            bot.reload_extension(arg)
            summary += f'🟢 {arg} sucessfully reloaded\n'

        except ExtensionNotLoaded as err:
            log.warning(err)
            summary += f'🟡 {arg} wasn\'t loaded\n'

        except ExtensionNotFound as err:
            log.warning(err)
            summary += f'🟠 {arg} doesn\'t exist\n'

        except Exception as err:
            log.error(err)
            summary += f'🔴 {arg} failed to reload\n'
        
        else:
            success += 1
        finally:
            total += 1
    
    # TODO Maybe use discord pages for a nicer interface
    # Feedback
    if not silent:
        if total == 0:
            await ctx.channel.send(f'No extensions have reloaded')
            return
        if verbose:
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