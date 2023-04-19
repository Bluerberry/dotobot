
import logging
from os.path import basename

import discord
from discord import ExtensionAlreadyLoaded, ExtensionNotFound, ExtensionNotLoaded
from discord.ext import commands
from dotenv import load_dotenv

import util

# ---------------------> Logging setup

name = basename(__file__)[:-2]
log = logging.getLogger(name)

# ---------------------> Environment setup

load_dotenv()

# ---------------------> System cog

def setup(bot: commands.Bot) -> None:
    bot.add_cog(System(bot))
    log.info(f'Extension has been created: {name}')


def teardown(bot: commands.Bot) -> None:
    log.info(f'Extension has been destroyed: {name}')


class System(commands.Cog, name=name, description='Controls internal functionality'):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.command(name='summary', description='Provides summary of previous command, or reference command.')
    @util.default_command()
    async def summary(self, ctx: commands.Context, *_) -> None:

        # Finding summary to provide
        reference = ctx.message.reference
        if reference == None:
            summary = util.history.last()
        else:
            summary = util.history.search(reference.message_id)

        # Check if summary exists
        if summary == None:
            await ctx.reply('No summary found!', mention_author=False)
            log.warn('Failed to provide summary')
            return

        # Provide summary
        await summary.ctx.reply(embed=summary.embed, mention_author=False)

    @commands.command(name='load', description='Loads extensions by name.')
    @util.default_command(thesaurus={'a': 'all', 'q': 'quiet', 'v': 'verbose'})
    @util.summarized()
    @util.dev_only()
    async def load(self, ctx: commands.Context, flags: list[str], params: list[str]) -> discord.Embed:

        # Prepare extension paths
        if not params or 'all' in flags:
            params = list(util.yield_extensions(prefix_path=True))
        else:
            params = [util.extension_path(param) for param in params]

        # Load extensions
        success = 0
        summary = ''
        for ext in params:

            try:
                self.bot.load_extension(ext)
                summary += f'🟢 {util.extension_name(ext).capitalize()} sucessfully loaded\n'
                success += 1

            except ExtensionAlreadyLoaded as err:
                log.warning(err)
                summary += f'🟡 {util.extension_name(ext).capitalize()} was already loaded\n'

            except ExtensionNotFound as err:
                log.warning(err)
                summary += f'🟠 {util.extension_name(ext).capitalize()} doesn\'t exist\n'

            except Exception as err:
                log.error(err)
                summary += f'🔴 {util.extension_name(ext).capitalize()} failed to load\n'

        # Find status
        if (total := len(params)) == 0:
            status = 'No extensions have loaded'
        elif total == success:
            status = 'All extensions have loaded'
        else:
            status = f'{success} out of {total} extensions have loaded'

        # Build embed
        embed = util.default_embed(self.bot, 'Summary', status)
        embed.add_field(name='Extensions', value=f'```{summary}```')

        # Feedback
        if 'quiet' not in flags:
            if 'verbose' in flags:
                await ctx.reply(embed=embed, mention_author=False)
            else:
                await ctx.reply(status, mention_author=False)

        return embed


    @commands.command(name='unload', description='Unloads extensions by name.')
    @util.default_command(thesaurus={'a': 'all', 'q': 'quiet', 'v': 'verbose'})
    @util.summarized()
    @util.dev_only()
    async def unload(self, ctx: commands.Context, flags: list[str], params: list[str]) -> discord.Embed:

        # Prepare extension paths
        if not params or 'all' in flags:
            params = list(self.bot.extensions.keys())
        else:
            params = [util.extension_path(param) for param in params]

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
                success += 1

            except ExtensionNotLoaded as err:
                log.warning(err)
                summary += f'🟡 {util.extension_name(ext).capitalize()} was already unloaded\n'

            except ExtensionNotFound as err:
                log.warning(err)
                summary += f'🟠 {util.extension_name(ext).capitalize()} doesn\'t exist\n'

            except Exception as err:
                log.error(err)
                summary += f'🔴 {util.extension_name(ext).capitalize()} failed to unload\n'

        # Find status
        if (total := len(params)) == 0:
            status = 'No extensions have unloaded'
        elif total == success:
            status = 'All extensions have unloaded'
        else:
            status = f'{success} out of {total} extensions have unloaded'

        # Build embed
        embed = util.default_embed(self.bot, 'Summary', status)
        embed.add_field(name='Extensions', value=f'```{summary}```')

        # Feedback
        if 'quiet' not in flags:
            if 'verbose' in flags:
                await ctx.reply(embed=embed, mention_author=False)
            else:
                await ctx.reply(status, mention_author=False)

        return embed


    @commands.command(name='reload', description='Reloads extensions by name.')
    @util.default_command(thesaurus={'a': 'all', 'q': 'quiet', 'v': 'verbose'})
    @util.summarized()
    @util.dev_only()
    async def reload(self, ctx: commands.Context, flags: list[str], params: list[str]) -> discord.Embed:

        # Prepare extension paths
        if not params or 'all' in flags:
            params = list(self.bot.extensions.keys())
        else:
            params = [util.extension_path(param) for param in params]

        # Reload extensions
        success = 0
        summary = ''
        for ext in params:

            try:
                self.bot.reload_extension(ext)
                summary += f'🟢 {util.extension_name(ext).capitalize()} sucessfully reloaded\n'
                success += 1

            except ExtensionNotLoaded as err:
                log.warning(err)
                summary += f'🟡 {util.extension_name(ext).capitalize()} wasn\'t loaded\n'

            except ExtensionNotFound as err:
                log.warning(err)
                summary += f'🟠 {util.extension_name(ext).capitalize()} doesn\'t exist\n'

            except Exception as err:
                log.error(err)
                summary += f'🔴 {util.extension_name(ext).capitalize()} failed to reload\n'

        # Feedback
        if 'silent' not in flags:
            if (total := len(params)) == 0:
                status = 'No extensions have reloaded'
            elif total == success:
                status = 'All extensions have reloaded'
            else:
                status = f'{success} out of {total} extensions have reloaded'

        # Build embed
        embed = util.default_embed(self.bot, 'Summary', status)
        embed.add_field(name='Extensions', value=f'```{summary}```')

        # Feedback
        if 'quiet' not in flags:
            if 'verbose' in flags:
                await ctx.reply(embed=embed, mention_author=False)
            else:
                await ctx.reply(status, mention_author=False)

        return embed


    @commands.command(name='status', description='Displays extension status')
    @util.default_command(thesaurus={'a': 'all'})
    async def status(self, ctx: commands.Context, flags: list[str], params: list[str]) -> None:

        known  = list(util.yield_extensions(prefix_path=True))
        loaded = list(self.bot.extensions.keys())

        # Prepare extension paths
        if not params or 'all' in flags:
            params = known
        else:
            params = [util.extension_path(param) for param in params]

        # Create summary
        active = 0
        summary = ''
        for ext in params:
            if ext not in known:
                summary += f'🟠 {util.extension_name(ext).capitalize()} doesn\'t exist\n'
            elif ext in loaded:
                summary += f'🟢 {util.extension_name(ext).capitalize()} is activated\n'
                active += 1
            else:
                summary += f'🔴 {util.extension_name(ext).capitalize()} is deactivated\n'

        # Feedback
        if (total := len(params)) == 0:
            status = 'No extensions are active'
        elif total == active:
            status = 'All extensions are active'
        else:
            status = f'{active} out of {total} extensions are active'

        embed = util.default_embed(self.bot, 'Status', status)
        embed.add_field(name='Extensions', value=f'```{summary}```')
        await ctx.reply(embed=embed, mention_author=False)