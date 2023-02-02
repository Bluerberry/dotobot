
from util import extract_flags, yield_extensions
from os.path import basename

name = basename(__file__)[:-2]

# ---------------------> Logging setup

import logging
log = logging.getLogger(name)

# ---------------------> System cog

from discord import ExtensionAlreadyLoaded, ExtensionNotLoaded, ExtensionNotFound
from discord.ext import commands

def setup(bot: commands.Bot) -> None:
    bot.add_cog(System(bot))
    log.info(f'Extension has been created: {name}')

def teardown(bot: commands.Bot) -> None:
    log.info(f'Extension has been destroyed: {name}')

class System(commands.Cog, name = name, description = 'Controls internal functionality'):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
    
    @commands.command(name = 'load')
    @extract_flags()
    async def load(self, ctx: commands.Context, flags, params) -> None:

        # Preperations
        total: int = 0
        success: int = 0
        summary: str = ''

        if not params or 'all' in flags:
            params = yield_extensions('extensions')

        # Load extensions
        for ext in params:

            try:
                self.bot.load_extension('extensions.' + ext)
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

    @commands.command(name = 'unload')
    @extract_flags()
    async def unload(self, ctx: commands.Context, flags, params) -> None:

        # Preperations
        total: int = 0
        success: int = 0
        summary: str = ''

        if not params or 'all' in flags:
            params = [ext[11:] for ext in self.bot.extensions.keys()]

        # Unload extensions
        for ext in params:
            
            total += 1
            if ext == 'system':
                summary += f'🔴 {ext} failed to unload\n'
                if 'silent' not in flags:
                    await ctx.channel.send('I wouldn\'t unload `system` if I were you')
                continue

            try:
                self.bot.unload_extension('extensions.' + ext)
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

    @commands.command(name = 'reload')
    @extract_flags()
    async def reload(self, ctx: commands.Context, flags, params) -> None:

        # Preperations
        total: int = 0
        success: int = 0
        summary: str = ''

        if not params or 'all' in flags:
            params = [ext[11:] for ext in self.bot.extensions.keys()]

        # Reload extensions
        for ext in params:

            try:
                self.bot.reload_extension('extensions.' + ext)
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
