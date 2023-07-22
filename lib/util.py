
import re as regex
from glob import iglob
from os import getenv
from os.path import join
from typing import Generator, Tuple

import dotenv
import discord
from discord.ext import commands

MIN_RELATIVE_OVERLAP = 0.5
FUZZY_OVERLAP_MARGIN = 1
MAX_RELATIVE_DISTANCE = 0.5
FUZZY_DISTANCE_MARGIN = 3


# ---------------------> Environment setup


dotenv.load_dotenv()


# ---------------------> Classes


class Dialog:
    def __init__(self, ctx: commands.Context) -> None:
        self.ctx = ctx
        self.dialog = None
    
    async def set(self, *args, **kwargs) -> discord.Message:
        if self.dialog == None:
            self.dialog = await self.ctx.reply(*args, **kwargs)
        else:
            self.dialog = await self.dialog.edit(*args, **kwargs)
        return self.dialog

    async def add(self, *args, **kwargs) -> discord.Message:
        return await self.ctx.reply(*args, **kwargs)

    async def cleanup(self) -> None:
        if self.dialog:
            await self.dialog.delete()

class Summary:
    def __init__(self, ctx: commands.Context, send_on_return: bool = True):
        self.ctx = ctx
        self.fields = {}
        self.send_on_return = send_on_return

    def make_embed(self) -> discord.Embed | None:
        if not self.header:
            return None

        embed = DefaultEmbed(self.ctx.bot, 'Summary', self.header)
        for name, value in self.fields.items():
            embed.add_field(name=name, value=value)

        return embed

    def set_header(self, header: str) -> None:
        self.header = header

    def set_field(self, name: str, value: str) -> None:
        self.fields[name] = value

class History:
    history = []

    def add(self, summary: Summary) -> None:
        self.history.append(summary) # Add to history
        self.history = self.history[:10]         # Trim history

    def last(self) -> Summary | None:
        if len(self.history) == 0:
            return None
        return self.history[-1]

    def search(self, id: int) -> Summary | None:
        for summary in self.history:
            if summary.ctx.message.id == id:
                return summary
        return None

class DefaultEmbed(discord.Embed):
    def __init__(self, bot: commands.Bot, title: str = '', description: str = '', author: bool = False, footer: bool = True, color: int = 0) -> None:
        palette = [
            discord.Colour.from_rgb(255, 89,  94 ), # Red
            discord.Colour.from_rgb(255, 202, 58 ), # Yellow
            discord.Colour.from_rgb(138, 201, 38 ), # Green
            discord.Colour.from_rgb(25,  130, 196), # Blue
            discord.Colour.from_rgb(106, 76,  147)  # Purple
        ]

        super().__init__(
            title=title,
            description=description,
            color=palette[color % 5]
        )

        if author:
            self.set_author(name=bot.user.name)
        if footer:
            self.set_footer(text=f'Powered by {bot.user.name}')

history = History()


# ---------------------> Wrappers


# Wraps around commands to split args into flags and params. Also gives summary if summarized
#   - incoming func MUST follow async (self, ctx, flags, vars, params) -> Any
#   - outgoing func follows async (self, ctx, *args, **kwargs) -> Any
#   - decorator Must be placed below @bot.command() decorator

def default_command(param_filter: str | None = None, thesaurus: dict[str, str] = {'q': 'quiet', 'v': 'verbose'}):
    def wrapper(func):
        async def wrapped(self, ctx, *, args: str = '', **_):
            SHORT_VAR_FILTER = r'-- ?(\w+) ?= ?(\w+)'
            LONG_VAR_FILTER = r'-- ?(\w+) ?= ?["“](.+)["“]'
            FLAG_FILTER = r'-- ?(\w+)'
            
            flags  = []
            vars   = []
            params = []

            # Filter out vars
            raw_vars = regex.findall(SHORT_VAR_FILTER, args)
            raw_vars.append(regex.findall(LONG_VAR_FILTER, args))
            args = regex.sub(SHORT_VAR_FILTER, '', args)
            args = regex.sub(LONG_VAR_FILTER, '', args)

            for var in raw_vars:
                key, value = var
                if key in thesaurus:
                    vars[thesaurus[key]] = value
                else:
                    vars[key] = value

            # Filter out flags
            raw_flags = regex.findall(FLAG_FILTER, args)
            args = regex.sub(FLAG_FILTER, '', args)

            for flag in raw_flags:
                if flag in thesaurus:
                    flags.append(thesaurus[flag])
                else:
                    flags.append(flag)
            
            # Filter parameters
            if param_filter == None:
                params.append(args)
            else:
                params = regex.findall(param_filter, args)

            # Call function
            return_value = await func(self, ctx, flags, vars, params)

            # Give summary
            if hasattr(func, 'summarized'):
                if return_value.send_on_return and 'quiet' not in flags:
                    if 'verbose' in flags:
                        await ctx.reply(embed=return_value.make_embed())
                    else:
                        await ctx.reply(return_value.header)

            return return_value
        
        wrapped.default_command = True
        return wrapped
    return wrapper

# Wraps around commands to add summary to history. Also gives summary if default_command
#   - incoming func MUST return Summary
#   - outgoing func signature does not change
#   - decorator MUST be placed below @bot.command() decorator

def summarized():
    def wrapper(func):
        async def wrapped(self, ctx, *args, **kwargs):
            summary = await func(self, ctx, *args, **kwargs)
            history.add(summary)

            # Give summary
            if hasattr(func, 'default_command'):
                if summary.send_on_return and 'quiet' not in args[0]:
                    if 'verbose' in args[0]:
                        await ctx.reply(embed=summary.make_embed())
                    else:
                        await ctx.reply(summary.header)

            return summary
        
        wrapped.summarized = True
        return wrapped
    return wrapper

# Wraps around commands to make it dev only
#   - incoming func signature does not matter
#   - outgoing func signature does not change
#   - decorator MUST be placed below @bot.command() decorator

def dev_only():
    def predicate(ctx):
        return str(ctx.author.id) in getenv('DEVELOPER_IDS')    
    return commands.check(predicate)


# ---------------------> Utility Functions


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

# Sorts a list of options based on overlap with, and distance to the given query
#   - options is a list of strings to match the query to
#   - query is a string of non-zero length
#   - Return type is an ordered list of dictionaries with the fields { name, sanitized, overlap, distance }
#   - The return type is ordered first by the largest overlap, then by the smallest distance

def fuzzy_search(options: list[str], query: str) -> Tuple[bool, list[dict]]:
    def sanitize(input: str) -> str:
        output = input.lower()
        filter = regex.compile('[^\w ]')
        return filter.sub('', output)

    def overlap(a: str, b: str) -> int:
        m, n, best = len(a), len(b), 0
        lengths = [[0 for _ in range(n + 1)] for _ in range(2)]

        # Check values
        if m == 0 or n == 0:
            raise ValueError('Input strings must be of non-zero length')

        # Dynamic programming shenanigans keeping track of longest suffix
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if a[i - 1] == b[j - 1]:
                    lengths[i % 2][j] = lengths[(i - 1) % 2][j - 1] + 1
                    if lengths[i % 2][j] > best:
                        best = lengths[i % 2][j]
                else:
                    lengths[i % 2][j] = 0

        return best

    def distance(a: str, b: str) -> int:
        m, n = len(a), len(b)
        prev = [i for i in range(n + 1)]
        curr = [0 for _ in range(n + 1)]

        # Check values
        if m == 0 or n == 0:
            raise ValueError('Input strings must be of non-zero length')

        # Dynamic programming shenanigans
        for i in range(m):
            curr[0] = i + 1

            # Find edit cost
            for j in range(n):
                del_cost = prev[j + 1] + 1
                ins_cost = curr[j] + 1
                sub_cost = prev[j] + int(a[i] != b[j])
                curr[j + 1] = min(del_cost, ins_cost, sub_cost)

            # Copy curr to prev
            for j in range(n + 1):
                prev[j] = curr[j]

        return prev[n]

    # Sanitize input
    if len(options) < 1:
        return False, []

    # Sanitize options
    results = [{
     'name': option,
     'sanitized': sanitize(option),
     'overlap': None,
     'relative_overlap': None,
     'distance': None,
     'relative_distance': None
    } for option in options]

    # Calculate scores
    for result in results:
        result['overlap'] = overlap(query, result['sanitized'])
        result['relative_overlap'] = result['overlap'] / len(result['sanitized'])
        result['distance'] = distance(query, result['sanitized'])
        result['relative_distance'] = result['distance'] / len(result['sanitized'])

    # Sort results
    results.sort(key=lambda result: result['distance'])
    results.sort(key=lambda result: result['overlap'], reverse=True)

    # Check if results are conclusive
    conclusive = results[0]['relative_overlap'] > MIN_RELATIVE_OVERLAP and                   \
                 results[0]['relative_distance'] < MAX_RELATIVE_DISTANCE and (               \
                     len(results) < 2 or                                                     \
                     results[0]['overlap'] > results[1]['overlap'] + FUZZY_OVERLAP_MARGIN or \
                     results[0]['distance'] < results[1]['distance'] - FUZZY_DISTANCE_MARGIN \
                 )

    return conclusive, results