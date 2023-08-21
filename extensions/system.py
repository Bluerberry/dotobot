
import logging
from os.path import basename

import discord
import dotenv
import pony.orm as pony
from discord.ext import commands

import lib.entities as entities
import lib.util as util

# ---------------------> Logging setup


name = basename(__file__)[:-3]
log = logging.getLogger(name)


# ---------------------> Environment setup


dotenv.load_dotenv()


# ---------------------> System cog


def setup(bot: commands.Bot) -> None:
    with pony.db_session:
        if entities.Extension.exists(name=name):
            extension = entities.Extension.get(name=name)
            extension.active = True
        else:
            entities.Extension(name=name, active=True)

    bot.add_cog(System(bot))
    log.info(f'Extension has been created: {name}')

def teardown(bot: commands.Bot) -> None:
    with pony.db_session:
        extension = entities.Extension.get(name=name)
        extension.active = False
    
    log.info(f'Extension has been destroyed: {name}')

class System(commands.Cog, name=name, description='Controls internal functionality'):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot


    # ---------------------> Commands


    @commands.command(name='summary', description='Provides summary of previous command, or reference command.')
    @util.default_command()
    async def summary(self, ctx: commands.Context, flags: list[str], vars: dict, params: list[str]) -> None:

        # Finding summary to provide
        reference = ctx.message.reference
        if reference == None:
            summary = util.history.last()
        else:
            summary = util.history.search(reference.message_id)

        # Check if summary exists
        if summary == None:
            await ctx.reply('No summary found!')
            log.warn('Failed to provide summary')
            return

        # Provide summary
        await summary.ctx.reply(embed=summary.make_embed())

    @commands.command(name='load', description='Loads extensions by name.')
    @util.default_command(param_filter=r'(\w+)', thesaurus={'a': 'all', 'q': 'quiet', 'v': 'verbose'})
    @util.summarized()
    @util.dev_only()
    async def load(self, ctx: commands.Context, flags: list[str], vars: dict, params: list[str]) -> util.Summary:
        summary = util.Summary(ctx)

        # Prepare extension paths
        if not params or 'all' in flags:
            params = list(util.yield_extensions(prefix_path=True))
        else:
            params = [util.extension_path(param) for param in params]

        # Load extensions
        field = ''
        success = 0
        for ext in params:

            try:
                self.bot.load_extension(ext)
                field += f'🟢 {util.extension_name(ext).capitalize()} sucessfully loaded\n'
                success += 1

            except discord.ExtensionAlreadyLoaded as err:
                log.warning(err)
                field += f'🟡 {util.extension_name(ext).capitalize()} was already loaded\n'

            except discord.ExtensionNotFound as err:
                log.warning(err)
                field += f'🟠 {util.extension_name(ext).capitalize()} doesn\'t exist\n'

            except Exception as err:
                log.error(err)
                field += f'🔴 {util.extension_name(ext).capitalize()} failed to load\n'

        # Build summary
        if (total := len(params)) == 0:
            summary.set_header('No extension have loaded')
            summary.set_field('Extensions', field)
        elif total == success:
            summary.set_header('All extensions have loaded')
            summary.set_field('Extensions', field)
        else:
            summary.set_header(f'{success} out of {total} extensions have loaded')
            summary.set_field('Extensions', field)

        return summary

    @commands.command(name='unload', description='Unloads extensions by name.')
    @util.default_command(param_filter=r'(\w+)', thesaurus={'a': 'all', 'q': 'quiet', 'v': 'verbose'})
    @util.summarized()
    @util.dev_only()
    async def unload(self, ctx: commands.Context, flags: list[str], vars: dict, params: list[str]) -> util.Summary:
        summary = util.Summary(ctx)

        # Prepare extension paths
        if not params or 'all' in flags:
            params = list(self.bot.extensions.keys())
        else:
            params = [util.extension_path(param) for param in params]

        # Unload extensions
        field = ''
        success = 0
        for ext in params:

            if util.extension_name(ext) == 'system':
                field += f'🔴 {util.extension_name(ext).capitalize()} shouldn\'t unload\n'
                continue

            try:
                self.bot.unload_extension(ext)
                field += f'🟢 {util.extension_name(ext).capitalize()} sucessfully unloaded\n'
                success += 1

            except discord.ExtensionNotLoaded as err:
                log.warning(err)
                field += f'🟡 {util.extension_name(ext).capitalize()} was already unloaded\n'

            except discord.ExtensionNotFound as err:
                log.warning(err)
                field += f'🟠 {util.extension_name(ext).capitalize()} doesn\'t exist\n'

            except Exception as err:
                log.error(err)
                field += f'🔴 {util.extension_name(ext).capitalize()} failed to unload\n'

        # Build summary
        if (total := len(params)) == 0:
            summary.set_header('No extension have unloaded')
            summary.set_field('Extensions', field)
        elif total == success:
            summary.set_header('All extensions have unloaded')
            summary.set_field('Extensions', field)
        else:
            summary.set_header(f'{success} out of {total} extensions have unloaded')
            summary.set_field('Extensions', field)

        return summary

    @commands.command(name='reload', description='Reloads extensions by name.')
    @util.default_command(param_filter=r'(\w+)', thesaurus={'a': 'all', 'q': 'quiet', 'v': 'verbose'})
    @util.summarized()
    @util.dev_only()
    async def reload(self, ctx: commands.Context, flags: list[str], vars: dict, params: list[str]) -> discord.Embed:
        summary = util.Summary(ctx)

        # Prepare extension paths
        if not params or 'all' in flags:
            params = list(self.bot.extensions.keys())
        else:
            params = [util.extension_path(param) for param in params]

        # Reload extensions
        field = ''
        success = 0
        for ext in params:

            try:
                self.bot.reload_extension(ext)
                field += f'🟢 {util.extension_name(ext).capitalize()} sucessfully reloaded\n'
                success += 1

            except discord.ExtensionNotLoaded as err:
                log.warning(err)
                field += f'🟡 {util.extension_name(ext).capitalize()} wasn\'t loaded\n'

            except discord.ExtensionNotFound as err:
                log.warning(err)
                field += f'🟠 {util.extension_name(ext).capitalize()} doesn\'t exist\n'

            except Exception as err:
                log.error(err)
                field += f'🔴 {util.extension_name(ext).capitalize()} failed to reload\n'

        # Build summary
        if (total := len(params)) == 0:
            summary.set_header('No extension have reloaded')
            summary.set_field('Extensions', field)
        elif total == success:
            summary.set_header('All extensions have reloaded')
            summary.set_field('Extensions', field)
        else:
            summary.set_header(f'{success} out of {total} extensions have reloaded')
            summary.set_field('Extensions', field)

        return summary

    @commands.command(name='status', description='Displays extension status')
    @util.default_command(param_filter=r'(\w+)', thesaurus={'a': 'all'})
    async def status(self, ctx: commands.Context, flags: list[str], vars: dict, params: list[str]) -> None:
        summary = util.Summary(ctx)
        known  = list(util.yield_extensions(prefix_path=True))
        loaded = list(self.bot.extensions.keys())

        # Prepare extension paths
        if not params or 'all' in flags:
            params = known
        else:
            params = [util.extension_path(param) for param in params]

        # Create summary
        field = ''
        active = 0
        for ext in params:
            if ext not in known:
                field += f'🟠 {util.extension_name(ext).capitalize()} doesn\'t exist\n'
            elif ext in loaded:
                field += f'🟢 {util.extension_name(ext).capitalize()} is activated\n'
                active += 1
            else:
                field += f'🔴 {util.extension_name(ext).capitalize()} is deactivated\n'

        # Feedback
        if (total := len(params)) == 0:
            summary.set_header('No extensions are active')
            summary.set_field('Extensions', field)

        elif total == active:
            summary.set_header('All extensions are active')
            summary.set_field('Extensions', field)
            
        else:
            summary.set_header(f'{active} out of {total} extensions are active')
            summary.set_field('Extensions', field)

        await ctx.reply(embed=summary.make_embed())