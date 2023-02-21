
import logging
from os.path import basename

import discord
from discord import ExtensionAlreadyLoaded, ExtensionNotFound, ExtensionNotLoaded
from discord.ext import commands

import util

# ---------------------> Logging setup

name = basename(__file__)[:-2]
log = logging.getLogger(name)

# ---------------------> System cog

def setup(bot: commands.Bot) -> None:
    bot.add_cog(System(bot))
    log.info(f'Extension has been created: {name}')


def teardown(bot: commands.Bot) -> None:
    log.info(f'Extension has been destroyed: {name}')


class System(commands.Cog, name=name, description='Controls internal functionality'):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
    
    @util.dev_only()
    @commands.command(name='load', description='Loads extensions by name.')
    @util.default_command(thesaurus={'v': 'verbose', 's': 'silent'})
    async def load(self, ctx: commands.Context, flags: list[str], params: list[str]) -> None:

        # Prepare extension paths
        if not params or 'all' in flags:
            params = util.yield_extensions(prefix_path=True)
        else:
            params = map(util.extension_path, params)

        # Load extensions
        success = 0
        summary = ''
        for ext in params: 

            try:
                self.bot.load_extension(ext)
                summary += f'🟢 {util.extension_name(ext).capitalize()} sucessfully loaded\n'

            except ExtensionAlreadyLoaded as err:
                log.warning(err)
                summary += f'🟡 {util.extension_name(ext).capitalize()} was already loaded\n'

            except ExtensionNotFound as err:
                log.warning(err)
                summary += f'🟠 {util.extension_name(ext).capitalize()} doesn\'t exist\n'

            except Exception as err:
                log.error(err)
                summary += f'🔴 {util.extension_name(ext).capitalize()} failed to load\n'

            else:
                success += 1

        # Feedback
        if 'silent' not in flags:
            if total := len(params) == 0:
                status = 'No extensions have loaded'
            elif total == success:
                status = 'All extensions have loaded'
            else:
                status = f'{success} out of {total} extensions have loaded'

            if 'verbose' in flags:
                embed = util.default_embed(self.bot, 'Summary', status)
                embed.add_field(name='Extensions', value=f'```{summary}```')
                await ctx.reply(embed=embed, mention_author=False)
            else:
                await ctx.reply(status, mention_author=False)


    @util.dev_only()
    @commands.command(name='unload', description='Unloads extensions by name')
    @util.default_command(thesaurus={'v': 'verbose', 's': 'silent'})
    async def unload(self, ctx: commands.Context, flags: list[str], params: list[str]) -> None:

        # Prepare extension paths
        if not params or 'all' in flags:
            params = list(self.bot.extensions.keys())
        else:
            params = map(util.extension_path, params)

        # Unload extensions
        success = 0
        summary = ''
        for ext in params:
            
            if util.extension_name(ext) == 'system':
                summary += f'🔴 {util.extension_name(ext).capitalize()} should\'nt unload\n'
                continue

            try:
                self.bot.unload_extension(ext)
                summary += f'🟢 {util.extension_name(ext).capitalize()} sucessfully unloaded\n'

            except ExtensionNotLoaded as err:
                log.warning(err)
                summary += f'🟡 {util.extension_name(ext).capitalize()} was already unloaded\n'

            except ExtensionNotFound as err:
                log.warning(err)
                summary += f'🟠 {util.extension_name(ext).capitalize()} doesn\'t exist\n'

            except Exception as err:
                log.error(err)
                summary += f'🔴 {util.extension_name(ext).capitalize()} failed to unload\n'

            else:
                success += 1

        # Feedback
        if 'silent' not in flags:
            if total := len(params) == 0:
                status = 'No extensions have unloaded'
            elif total == success:
                status = 'All extensions have unloaded'
            else:
                status = f'{success} out of {total} extensions have unloaded'

            if 'verbose' in flags:
                embed = util.default_embed(self.bot, 'Summary', status)
                embed.add_field(name='Extensions', value=f'```{summary}```')
                await ctx.reply(embed=embed, mention_author=False)
            else:
                await ctx.reply(status, mention_author=False)


    @util.dev_only()
    @commands.command(name='reload', description='Reloads extensions by name')
    @util.default_command(thesaurus={'v': 'verbose', 's': 'silent'})
    async def reload(self, ctx: commands.Context, flags: list[str], params: list[str]) -> None:

        # Prepare extension paths
        if not params or 'all' in flags:
            params = list(self.bot.extensions.keys())
        else:
            params = map(util.extension_path, params)

        # Reload extensions
        success = 0
        summary = ''
        for ext in params:

            try:
                self.bot.reload_extension(ext)
                summary += f'🟢 {util.extension_name(ext).capitalize()} sucessfully reloaded\n'

            except ExtensionNotLoaded as err:
                log.warning(err)
                summary += f'🟡 {util.extension_name(ext).capitalize()} wasn\'t loaded\n'

            except ExtensionNotFound as err:
                log.warning(err)
                summary += f'🟠 {util.extension_name(ext).capitalize()} doesn\'t exist\n'

            except Exception as err:
                log.error(err)
                summary += f'🔴 {util.extension_name(ext).capitalize()} failed to reload\n'

            else:
                success += 1

        # Feedback
        if 'silent' not in flags:
            if total := len(params) == 0:
                status = 'No extensions have reloaded'
            elif total == success:
                status = 'All extensions have reloaded'
            else:
                status = f'{success} out of {total} extensions have reloaded'

            if 'verbose' in flags:
                embed = util.default_embed(self.bot, 'Summary', status)
                embed.add_field(name='Extensions', value=f'```{summary}```')
                await ctx.reply(embed=embed, mention_author=False)
            else:
                await ctx.reply(status, mention_author=False)
