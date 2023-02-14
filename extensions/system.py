
import util
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
    @util.extract_flags()
    async def load(self, ctx: commands.Context, flags, params) -> None:

        # Preperations
        total: int = 0
        success: int = 0
        summary: str = ''

        if not params or 'all' in flags:
            params = util.yield_extensions('extensions')

        # Load extensions
        for ext in params:

            try:
                self.bot.load_extension('extensions.' + ext)
                summary += f'🟢 {ext.capitalize()} sucessfully loaded\n'

            except ExtensionAlreadyLoaded as err:
                log.warning(err)
                summary += f'🟡 {ext.capitalize()} was already loaded\n'

            except ExtensionNotFound as err:
                log.warning(err)
                summary += f'🟠 {ext.capitalize()} doesn\'t exist\n'

            except Exception as err:
                log.error(err)
                summary += f'🔴 {ext.capitalize()} failed to load\n'

            else:
                success += 1
            finally:
                total += 1

        # Feedback
        if 'silent' not in flags:
            if total == 0:
                status = 'No extensions have loaded'
            elif total == success:
                status = 'All extensions have loaded'
            else:
                status = f'{success} out of {total} extensions have loaded'

            if 'verbose' in flags:
                embed = util.default_embed(self.bot, 'Summary', status)
                embed.add_field(name = 'Extensions', value = f'```{summary}```')
                await ctx.reply(embed = embed, mention_author = False)
            else:
                await ctx.reply(status, mention_author = False)


    @commands.command(name = 'unload')
    @util.extract_flags()
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
                summary += f'🔴 {ext.capitalize()} should\'nt unload\n'
                continue

            try:
                self.bot.unload_extension('extensions.' + ext)
                summary += f'🟢 {ext.capitalize()} sucessfully unloaded\n'

            except ExtensionNotLoaded as err:
                log.warning(err)
                summary += f'🟡 {ext.capitalize()} was already unloaded\n'

            except ExtensionNotFound as err:
                log.warning(err)
                summary += f'🟠 {ext.capitalize()} doesn\'t exist\n'

            except Exception as err:
                log.error(err)
                summary += f'🔴 {ext.capitalize()} failed to unload\n'

            else:
                success += 1

        # Feedback
        if 'silent' not in flags:
            if total == 0:
                status = 'No extensions have unloaded'
            elif total == success:
                status = 'All extensions have unloaded'
            else:
                status = f'{success} out of {total} extensions have unloaded'

            if 'verbose' in flags:
                embed = util.default_embed(self.bot, 'Summary', status)
                embed.add_field(name = 'Extensions', value = f'```{summary}```')
                await ctx.reply(embed = embed, mention_author = False)
            else:
                await ctx.reply(status, mention_author = False)


    @commands.command(name = 'reload')
    @util.extract_flags()
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
                summary += f'🟢 {ext.capitalize()} sucessfully reloaded\n'

            except ExtensionNotLoaded as err:
                log.warning(err)
                summary += f'🟡 {ext.capitalize()} wasn\'t loaded\n'

            except ExtensionNotFound as err:
                log.warning(err)
                summary += f'🟠 {ext.capitalize()} doesn\'t exist\n'

            except Exception as err:
                log.error(err)
                summary += f'🔴 {ext.capitalize()} failed to reload\n'

            else:
                success += 1
            finally:
                total += 1

        # Feedback
        if 'silent' not in flags:
            if total == 0:
                status = 'No extensions have reloaded'
            elif total == success:
                status = 'All extensions have reloaded'
            else:
                status = f'{success} out of {total} extensions have reloaded'

            if 'verbose' in flags:
                embed = util.default_embed(self.bot, 'Summary', status)
                embed.add_field(name = 'Extensions', value = f'```{summary}```')
                await ctx.reply(embed = embed, mention_author = False)
            else:
                await ctx.reply(status, mention_author = False)
