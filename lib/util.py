
from __future__ import annotations

import asyncio
import re as regex
from glob import iglob
from os import getenv
from os.path import join
from typing import Any, Generator, Tuple

import dotenv
import errors
import parsing

import discord
from discord.ext import commands

MIN_RELATIVE_OVERLAP = 0.5
FUZZY_OVERLAP_MARGIN = 1
MAX_RELATIVE_DISTANCE = 0.5
FUZZY_DISTANCE_MARGIN = 3

# ---------------------> Environment setup


dotenv.load_dotenv()


# ---------------------> UI Classes


class ContinueCancelMenu(discord.ui.View):
    def __init__(self, authorised_user: discord.User, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.authorised_user = authorised_user
        self.responded = asyncio.Event()
        self.result = None

    async def await_response(self) -> bool:
        await self.responded.wait()
        self.disable_all_items()
        return self.result

    @discord.ui.button(label='Continue', style=discord.ButtonStyle.green, emoji='👍')
    async def override(self, _, interaction: discord.Interaction) -> None:
        if interaction.user != self.authorised_user:
            await interaction.response.send_message('You are not authorised to do that.', ephemeral=True)
            return
        
        await interaction.response.defer()
        self.result = True
        self.responded.set()

    @discord.ui.button(label='Abort', style=discord.ButtonStyle.red, emoji='👶')
    async def abort(self, _, interaction: discord.Interaction) -> None:
        if interaction.user != self.authorised_user:
            await interaction.response.send_message('You are not authorised to do that.', ephemeral=True)
            return

        await interaction.response.defer()
        self.result = False
        self.responded.set()


# ---------------------> Utility classes


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

class ANSIFactory:
    def __init__(self) -> None:
        self.text = '```ansi\n[0m'
    
    def __str__(self) -> str:
        return self.text + '[0m```'
    
    def add_raw(self, text: str) -> None:
        self.text += text
    
    def add(self, text: str, colour: str = 'default', stroke: str = 'default') -> None:
        self.text += '[' # Start escape sequence
        
        # Set stroke
        if stroke == 'default':
            self.text += '0;'
        elif stroke == 'bold':
            self.text += '1;'
        elif stroke == 'underline':
            self.text += '4;'
        else:
            raise ValueError('Invalid stroke given')
        
        # Set colour
        if colour == 'default':
            self.text += '39m'
        elif colour == 'grey':
            self.text += '30m'
        elif colour == 'red':
            self.text += '31m'
        elif colour == 'green':
            self.text += '32m'
        elif colour == 'yellow':
            self.text += '33m'
        elif colour == 'blue':
            self.text += '34m'
        elif colour == 'magenta':
            self.text += '35m'
        elif colour == 'cyan':
            self.text += '36m'
        elif colour == 'white':
            self.text += '37m'
        else:
            raise ValueError('Invalid colour given')
        
        # Add text
        self.text += text + '[0m'

class SearchItem:
    def __init__(self, item: Any, text: str) -> None:
        self.item = item
        self.text = text

        self.sanitized         = None
        self.overlap           = None
        self.relative_overlap  = None
        self.distance          = None
        self.relative_distance = None
        self.ranking           = None

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
    def __init__(self, ctx: commands.Context, send_on_return: bool = True) -> None:
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
        self.history.append(summary)
        self.history = self.history[-10:]

    def last(self) -> Summary | None:
        if len(self.history) == 0:
            return None
        return self.history[-1]

    def search(self, id: int) -> Summary | None:
        for summary in self.history:
            if summary.ctx.message.id == id:
                return summary
        return None

history = History()

# ---------------------> Wrappers


# Wraps around commands to split args into flags, params and variables using regex
#   - incoming func MUST follow async (self, ctx, dialog, summary, flags, vars, params) -> Any
#   - outgoing func follows async (self, ctx, *, raw: str = '', **args) -> Any
#   - decorator MUST be placed below @bot.command() decorator

def regex_command(param_filter: str = r'([^ ]+)', thesaurus: dict[str, str] = {}):
    def decorator(func):
        if hasattr(func, 'signature_command'):
            raise errors.WrapperError('Signature commands and regex commands are mutually exclusive')
        if hasattr(func, 'regex_command'):
            raise errors.WrapperError('Method is already a regex command')

        async def wrapped(self, ctx: commands.Context, *, raw: str = '', **_) -> None:
            SHORT_VAR_FILTER = r'-- ?([^ ]+) ?= ?([^ ]+)'
            LONG_VAR_FILTER = r'-- ?([^ ]+) ?= ?["“](.+)["“]'
            FLAG_FILTER = r'-- ?([^ ]+)'
            
            flags, vars, params = [], {}, []
            dialog = feedback.Dialog(ctx)
            summary = feedback.Summary(ctx)
            summary.set_header(f'Resolved {ctx.prefix}{ctx.command.name}')

            # Filter out vars
            raw_vars = regex.findall(LONG_VAR_FILTER, raw)
            raw = regex.sub(LONG_VAR_FILTER, '', raw)
            raw_vars.extend(regex.findall(SHORT_VAR_FILTER, raw))
            raw = regex.sub(SHORT_VAR_FILTER, '', raw)

            for var in raw_vars:
                key, value = var
                if key in thesaurus:
                    key = thesaurus[key]
                vars[key] = value

            # Filter out flags
            raw_flags = regex.findall(FLAG_FILTER, raw)
            raw = regex.sub(FLAG_FILTER, '', raw)

            for flag in raw_flags:
                if flag in thesaurus:
                    flag = thesaurus[flag]
                flags.append(flag)
            
            # Filter out parameters
            params = regex.findall(param_filter, raw)

            # Invoke command
            return_value = await func(self, ctx, dialog, summary, flags, vars, params)
            if summary.send_on_return and 'quiet' not in flags:
                if 'verbose' in flags:
                    await dialog.add(embed=summary.make_embed())
                else:
                    await dialog.add(summary.header)

            await dialog.cleanup()
        
        wrapped.default_command = True
        return wrapped
    return decorator

# Wraps around commands to match args to a signature, catches illegal commands and irrelevant arguments
#   - incoming func MUST follow async (self, ctx, dialog, summary, flags, vars, params) -> Any
#   - outgoing func follows async (self, ctx, *, raw: str = '', **args) -> Any
#   - decorator MUST be placed below @bot.command() decorator

def signature_command(raw_signature: str, thesaurus: dict[str, str] = {}):
    signature = parsing.Signature(raw_signature, {}) # TODO import signature dictionary from settings

    def decorator(func):
        if hasattr(func, 'signature_command'):
            raise errors.WrapperError('Method is already a signature command')
        if hasattr(func, 'regex_command'):
            raise errors.WrapperError('Signature commands and regex commands are mutually exclusive')

        async def wrapped(self, ctx: commands.Context, *, raw: str = '', **_) -> None:
            dialog  = feedback.Dialog(ctx)
            summary = feedback.Summary(ctx)
            summary.set_header(f'Resolved {ctx.prefix}{ctx.command.name}')

            try: # Parse command
                command = parsing.Command(raw, {}, thesaurus) # TODO import command dictionary from settings

            except Exception as err:
                if isinstance(err, parsing.errors.UnknownObject):
                    summary.set_header('Internal error')
                    summary.set_field('Unknown Object', f'Congratulations, you found a massive internal issue! Please report this to the developers, thanks bby <3')

                elif isinstance(err, parsing.errors.UnknownOperator):
                    summary.set_header('Internal error')
                    summary.set_field('Unknown Operator', f'Your command contains an unknown operator. This is a massive internal issue! Please report this to the developers, thanks bby <3')
                
                else:
                    summary.set_header('Invalid command')
                    summary.set_field('Expected signature', f'Given commands are expected to follow the following signature `{signature.raw}`. For more information, use the `help` command.')

                    if isinstance(err, parsing.errors.UnexpectedToken):
                        summary.set_field('Unexpected token', f'Found unexpected token `{err.token.raw}`, in given command `{command.raw}`.')
                    elif isinstance(err, parsing.errors.UnexpectedEOF):
                        summary.set_field('Unexpected EOF', f'Given command `{command.raw}` has floating operators')
                    else:
                        raise err

                # Give feedback
                await dialog.add(embed=summary.make_embed())
                await dialog.cleanup()
                history.add(summary)

                return

            # Match to signature
            result = signature.match(command)
            if not result.matched:
                summary.set_header('Invalid command')
                summary.set_field('Invalid command', f'Given command `{command.raw}` does not match the signature `{signature.raw}`.')
                summary.set_field('Expected signature', f'Given commands are expected to follow the following signature `{signature.raw}`. For more information, use the `help` command.')
                
                # Give feedback
                await dialog.add(embed=summary.make_embed())
                await dialog.cleanup()
                history.add(summary)

                return
        
            # Warn about unmatched parameters, flags and variables
            if result.unmatched_parameters:
                summary.set_field('Irrellevant parameters', f'Given command `{command.raw}` contains irrellevant parameters: `{", ".join(result.unmatched_parameters)}`. These parameters will be ignored.')
            if result.unmatched_flags:
                summary.set_field('Irrellevant flags', f'Given command `{command.raw}` contains irrellevant flags: `{", ".join(result.unmatched_flags)}`. These flags will be ignored.')
            if result.unmatched_variables:
                summary.set_field('Irrellevant variables', f'Given command `{command.raw}` contains irrellevant variables: `{", ".join(result.unmatched_variables)}`. These variables will be ignored.')

            # Invoke command
            return_value = await func(self, ctx, dialog, summary, result.unmatched_parameters, result.matched_flags, result.matched_variables)
            if summary.send_on_return and 'quiet' not in result.matched_flags:
                if 'verbose' in result.matched_flags:
                    await dialog.add(embed=summary.make_embed())
                else:
                    await dialog.add(summary.header)

            await dialog.cleanup()

        wrapped.signature_command = True
        return wrapped
    return decorator

# Wraps around commands to make it dev only
#   - incoming func signature does not matter
#   - outgoing func signature does not change
#   - decorator MUST be placed below @bot.command() decorator

def dev_only():
    def predicate(ctx: commands.Context):
        return str(ctx.author.id) in getenv('DEVELOPER_IDS')    
    return commands.check(predicate)


# ---------------------> Utility Functions


# Yields all extension files in path.
#   - sys_path contains path to extensions                  default is 'extensions'
#   - prefix_path toggles prefixing with extension path     default is False
#   - recursive toggles recursive search                    default is True

def yield_extensions(sys_path: str = 'extensions', prefix_path: bool = False, recursive: bool = True) -> Generator[str, None, None]:
    sys_path = join(sys_path, '**/*.py' if recursive else '*.py')     # Build path dependent on requirements
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

def fuzzy_search(options: list[SearchItem], query: str) -> Tuple[bool, list[SearchItem]]:
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
        return True, []

    # Calculate scores
    for option in options:
        option.sanitized = sanitize(option.text)
        option.overlap = overlap(query, option.sanitized)
        option.relative_overlap = option.overlap / len(option.sanitized)
        option.distance = distance(query, option.sanitized)
        option.relative_distance = option.distance / len(option.sanitized)

    # Sort options
    options.sort(key=lambda option: option.distance)
    options.sort(key=lambda option: option.overlap, reverse=True)

    for ranking, option in enumerate(options, start=1):
        option.ranking = ranking

    # Check if options are conclusive
    conclusive = options[0].relative_overlap > MIN_RELATIVE_OVERLAP and                \
                 options[0].relative_distance < MAX_RELATIVE_DISTANCE and (            \
                     len(options) < 2 or                                               \
                     options[0].overlap > options[1].overlap + FUZZY_OVERLAP_MARGIN or \
                     options[0].distance < options[1].distance - FUZZY_DISTANCE_MARGIN \
                 )

    return conclusive, options