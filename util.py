
# Wraps around commands to split args into flags and params.
#  - func MUST follow async (self, ctx, flags, params) -> Any
#  - decorator should be placed below @bot.command() decorator

def extract_flags():
    def wrapper(func):
        async def wrapped(self, ctx, *args, **kwargs):
            flags  = []
            params = []

            for arg in list(args):
                if arg.startswith('--'):
                    flags.append(arg[2:])
                else:
                    params.append(arg)

            return await func(self, ctx, flags, params)
        return wrapped
    return wrapper

# Yields all extension files in path.
#  - import_path prefixes extension with import path
#  - recursive goes deeper than one directory

from glob import iglob
from os.path import join
import re as regex

def yield_extensions(path, import_path = False, recursive = True):
    path = join(path, '.\\**\\*.py' if recursive else '.\\*.py')        # Build path dependent on requirements
    for file in iglob(path, recursive = True):                          # Use iglob to match all python files
        components = regex.findall(r'\w+', file[:-3])                   # Split into components and trim extension
        yield '.'.join(components) if import_path else components[-1]   # Either return composit or last component

# Returns default, empty embed.
#   - title & description are optional header strings.
#   - author toggles author                       default is false
#   - footer toggles footer                       default is true
#   - color loops through rainbow color palette   default is red

import discord
from discord.ext import commands

def default_embed(bot: commands.Bot, title: str = '', description: str = '', author: bool = False, footer: bool = True, color: int = 0) -> discord.Embed:
    palette = [
        discord.Colour.from_rgb(255, 89,  94 ),
        discord.Colour.from_rgb(255, 202, 58 ),
        discord.Colour.from_rgb(138, 201, 38 ),
        discord.Colour.from_rgb(25,  130, 196),
        discord.Colour.from_rgb(106, 76,  147)
    ]
    
    embed = discord.Embed(
        title = title,
        description = description,
        color = palette[color % 5]
    )

    if author:
        embed.set_author(name=bot.user.name) # TODO maybe add an icon?
    if footer:
        embed.set_footer(text=f'Powered by {bot.user.name}')

    return embed