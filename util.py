
import re as regex
from glob import iglob
from os import getenv
from os.path import join
from typing import Generator

import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

# ---------------------> Summary container

class Summary:
    embed = None
    ctx   = None

summary = Summary()

# ---------------------> Utility functions

# Wraps around commands to make it dev only
#   - decorator should be placed above @bot.command() decorator

def dev_only():
    def predicate(ctx):
        return str(ctx.author.id) in getenv('DEVELOPER_IDS')
    return commands.check(predicate)

# Wraps around commands to split args into flags and params.
#   - func MUST follow async (self, ctx, flags, params) -> discord.Embed
#   - decorator should be placed below @bot.command() decorator

def default_command(thesaurus: dict[str, str] = None):
    def wrapper(func):
        async def wrapped(self, ctx, *args, **_):
            flags  = []
            params = []

            for arg in list(args):

                # Parse flag
                if arg.startswith('-'):
                    flag = arg[1:]

                    # Translate synonyms into default
                    if flag in thesaurus.keys():
                        flag = thesaurus[flag]

                    flags.append(flag)
                
                # Parse parameter
                else:
                    params.append(arg)

            # Feedback
            summary.embed = await func(self, ctx, flags, params)
            summary.ctx = ctx

            if 'verbose' in flags and 'silent' not in flags:
                await ctx.reply(embed=summary.embed, mention_author=False)
                
        return wrapped
    return wrapper

# Returns default, empty embed.
#   - title & description are header strings                default is empty
#   - author toggles author                                 default is False
#   - footer toggles footer                                 default is True
#   - color loops through rainbow color palette             default is red

def default_embed(bot: commands.Bot, title: str = '', description: str = '', author: bool = False, footer: bool = True, color: int = 0) -> discord.Embed:
    palette = [
        discord.Colour.from_rgb(255, 89,  94 ), # Red
        discord.Colour.from_rgb(255, 202, 58 ), # Yellow
        discord.Colour.from_rgb(138, 201, 38 ), # Green
        discord.Colour.from_rgb(25,  130, 196), # Blue
        discord.Colour.from_rgb(106, 76,  147)  # Purple
    ]
    
    embed = discord.Embed(
        title=title,
        description=description,
        color=palette[color % 5]
    )

    if author:
        embed.set_author(name=bot.user.name) # TODO maybe add an icon?
    if footer:
        embed.set_footer(text=f'Powered by {bot.user.name}')

    return embed

# Yields all extension files in path.
#   - sys_path contains path to extensions                  default is 'extensions'
#   - prefix_path toggles prefixing with extension path     default is False
#   - recursive toggles recursive search                    default is True

def yield_extensions(sys_path: str = 'extensions', prefix_path: bool = False, recursive: bool = True) -> Generator[str, None, None]:
    sys_path = join(sys_path, '**\\*.py' if recursive else '*.py')     # Build path dependent on requirements
    for file in iglob(sys_path, recursive=recursive):                  # Use iglob to match all python files
        components = regex.findall(r'\w+', file)[:-1]                  # Split into components and trim extension
        yield '.'.join(components) if prefix_path else components[-1]  # Either return import path or extension name

# Finds extension in sys path, returns full extension path if found
#   - extension contains extension to search for
#   - sys_path contains path to extensions                  default is 'extensions'
#   - recursive toggles recursive search                    default is True

def extension_path(extension: str, sys_path: str = 'extensions', recursive: bool = True) -> str:
    sys_path = join(sys_path, '**' if recursive else '', f'{extension_name(extension)}.py')  # Build path dependent on requirement
    for file in iglob(sys_path, recursive=recursive):                                        # Use iglob to match all python files
        components = regex.findall(r'\w+', file)[:-1]                                        # Split into components and trim extension
        return '.'.join(components)                                                          # Return full extension path
    return extension                                                                         # If not found return extension

# Returns extension name from extension path
#   - extension_path contains path to extension with `.` seperation

def extension_name(extension_path: str) -> str:
    return extension_path.split('.')[-1]
    palette = [
        discord.Colour.from_rgb(255, 89,  94 ), # Red
        discord.Colour.from_rgb(255, 202, 58 ), # Yellow
        discord.Colour.from_rgb(138, 201, 38 ), # Green
        discord.Colour.from_rgb(25,  130, 196), # Blue
        discord.Colour.from_rgb(106, 76,  147)  # Purple
    ]
    
    embed = discord.Embed(
        title=title,
        description=description,
        color=palette[color % 5]
    )

    if author:
        embed.set_author(name=bot.user.name) # TODO maybe add an icon?
    if footer:
        embed.set_footer(text=f'Powered by {bot.user.name}')

    return embed