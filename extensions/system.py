
import logging
import os
import random
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

    async def random_status(self) -> None:
        await self.bot.wait_until_ready()
        await self.bot.change_presence(activity=random.choice([
            discord.Activity(type=discord.ActivityType.watching, name='paint dry'),
            discord.Activity(type=discord.ActivityType.watching, name='grass grow'),
            discord.Activity(type=discord.ActivityType.watching, name='yall'),
            discord.Activity(type=discord.ActivityType.playing, name='with myself'),
            discord.Activity(type=discord.ActivityType.playing, name='with your feelings'),
            discord.Activity(type=discord.ActivityType.playing, name='with matches'),
            discord.Activity(type=discord.ActivityType.listening, name='to the voices'),
            discord.Activity(type=discord.ActivityType.listening, name='to belly sounds'),
            discord.Activity(type=discord.ActivityType.listening, name='to static'),
            discord.Activity(type=discord.ActivityType.competing, name='in the paralympics'),
        ]))


    # ---------------------> Events


    @commands.Cog.listener()
    async def on_ready(self) -> None:

        # Add all members from all guilds to database
        with pony.db_session:
            for guild in self.bot.guilds:
                for member in guild.members:
                    if self.bot.application_id == member.id:
                        continue

                    if entities.User.exists(discord_id=member.id):
                        log.debug(f'New user `{member.name}` ({member.id}) already known')
                        continue

                    entities.User(discord_id=member.id)
                    log.info(f'New user `{member.name}` ({member.id}) added to the database')

        # Set random status
        await self.random_status()
        log.debug('Random status set')
        log.info(f'Succesful login as {self.bot.user}')

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.User) -> None:

        # Find greet channel
        channel = self.bot.get_channel(int(os.getenv('GREET_CHANNEL_ID')))
        if channel == None:
            log.error(f'Failed to load greet channel ({os.getenv("GREET_CHANNEL_ID")})')
            return

        # Check if new user is already known
        with pony.db_session:
            if entities.User.exists(discord_id=member.id):
                log.debug(f'New user `{member.name}` ({member.id}) already known')
                return

            entities.User(discord_id=member.id)
            log.info(f'New user `{member.name}` ({member.id}) added to the database')

        # Send greetings
        await channel.send(f'Welcome {member.mention}, to {channel.guild.name}!')

    @commands.Cog.listener()
    async def on_command(self, ctx: commands.Context) -> None:
        log.info(f'Command `{ctx.command}` invoked by `{ctx.author}` ({ctx.author.id}) in `{ctx.guild}` ({ctx.guild.id})')

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        if isinstance(error, commands.errors.CommandNotFound):
            return

        log.error(error)


    # ---------------------> Commands


    @commands.command(name='summary', description='Provides summary of previous command, or reference command.')
    @util.default_command()
    async def summary(self, ctx: commands.Context, flags: list[str], vars: dict, params: list[str]) -> None:

        # Finding summary to provide
        reference = ctx.message.reference
        if reference == None:
            summary = util.history.last()
            log.debug(f'Following last-command branch for {ctx.prefix}{ctx.command}')

        else:
            summary = util.history.search(reference.message_id)
            log.debug(f'Following reference branch for {ctx.prefix}{ctx.command}')

        # Check if summary exists
        if summary == None:
            await ctx.reply('No summary found!')
            log.warn('Failed to provide summary')
            return

        # Provide summary
        await summary.ctx.reply(embed=summary.make_embed())

    @commands.command(name='load', description='Loads extensions by name.')
    @util.default_command(param_filter=r'(\w+)', thesaurus={'a': 'all'})
    @util.summarized()
    @util.dev_only()
    async def load(self, ctx: commands.Context, flags: list[str], vars: dict, params: list[str]) -> util.Summary:
        summary = util.Summary(ctx)

        if vars:
            variables = ', '.join([f'{key} = "{value}"' for key, value in vars.items()])
            log.warning(f'Redundant variables found: {variables}')
            summary.set_field('Redundant variables', f'This function does not accept variables, yet it found these: {variables}.')

        # Prepare extension paths
        if 'all' in flags:
            params = list(util.yield_extensions(prefix_path=True))
            log.debug(f'Following --all branch for {ctx.prefix}{ctx.command}')

        elif params:
            params = [util.extension_path(param) for param in params]
            log.debug(f'Following parameter branch for {ctx.prefix}{ctx.command}')

        else:
            summary.set_header('No extensions or flags provided')
            summary.set_field('Usage', f'`{ctx.prefix}status <extensions | --all> [--quiet | --verbose]`\nUse `{ctx.prefix}help status` for more information.')
            log.error('No extensions or flags provided')
            return summary

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
    @util.default_command(param_filter=r'(\w+)', thesaurus={'a': 'all'})
    @util.summarized()
    @util.dev_only()
    async def unload(self, ctx: commands.Context, flags: list[str], vars: dict, params: list[str]) -> util.Summary:
        summary = util.Summary(ctx)

        if vars:
            variables = ', '.join([f'{key} = "{value}"' for key, value in vars.items()])
            log.warning(f'Redundant variables found: {variables}')
            summary.set_field('Redundant variables', f'This function does not accept variables, yet it found these: {variables}.')

        # Prepare extension paths
        if 'all' in flags:
            params = list(self.bot.extensions.keys())
            log.debug(f'Following --all branch for {ctx.prefix}{ctx.command}')

        elif params:
            params = [util.extension_path(param) for param in params]
            log.debug(f'Following parameter branch for {ctx.prefix}{ctx.command}')

        else:
            summary.set_header('No extensions or flags provided')
            summary.set_field('Usage', f'`{ctx.prefix}unload <extensions | --all> [--quiet | --verbose]`\nUse `{ctx.prefix}help reload` for more information.')
            log.error('No extensions or flags provided')
            return summary

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
    @util.default_command(param_filter=r'(\w+)', thesaurus={'a': 'all'})
    @util.summarized()
    @util.dev_only()
    async def reload(self, ctx: commands.Context, flags: list[str], vars: dict, params: list[str]) -> util.Summary:
        summary = util.Summary(ctx)

        if vars:
            variables = ', '.join([f'{key} = "{value}"' for key, value in vars.items()])
            log.warning(f'Redundant variables found: {variables}')
            summary.set_field('Redundant variables', f'This function does not accept variables, yet it found these: {variables}.')

        # Prepare extension paths
        if 'all' in flags:
            params = list(self.bot.extensions.keys())
            log.debug(f'Following --all branch for {ctx.prefix}{ctx.command}')

        elif params:
            params = [util.extension_path(param) for param in params]
            log.debug(f'Following parameter branch for {ctx.prefix}{ctx.command}')

        else:
            summary.set_header('No extensions or flags provided')
            summary.set_field('Usage', f'`{ctx.prefix}reload <extensions | --all> [--quiet | --verbose]`\nUse `{ctx.prefix}help reload` for more information.')
            log.error('No extensions or flags provided')
            return summary

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
    @util.summarized()
    async def status(self, ctx: commands.Context, flags: list[str], vars: dict, params: list[str]) -> util.Summary:
        summary = util.Summary(ctx)
        known  = list(util.yield_extensions(prefix_path=True))
        loaded = list(self.bot.extensions.keys())

        if vars:
            variables = ', '.join([f'{key} = "{value}"' for key, value in vars.items()])
            log.warning(f'Redundant variables found: {variables}')
            summary.set_field('Redundant variables', f'This function does not accept variables, yet it found these: {variables}.')

        # Prepare extension paths
        if 'all' in flags:
            params = known
            log.debug(f'Following --all branch for {ctx.prefix}{ctx.command}')

        elif params:
            params = [util.extension_path(param) for param in params]
            log.debug(f'Following parameter branch for {ctx.prefix}{ctx.command}')

        else:
            summary.set_header('No extensions or flags provided')
            summary.set_field('Usage', f'`{ctx.prefix}status <extensions | --all> [--quiet | --verbose]`\nUse `{ctx.prefix}help status` for more information.')
            log.error('No extensions or flags provided')
            return summary

        # Check status
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

        return summary

    @commands.command(name='dump', description='Dumps bot log')
    @util.default_command()
    @util.dev_only()
    async def dump(self, ctx: commands.Context, flags: list[str], vars: dict, params: list[str]) -> None:
        try:
            with open('logs//main.log', 'br') as file:
                await ctx.reply(file=discord.File(file, 'main.log'))

        except Exception as err:
            await ctx.reply('Failed to dump log')
            log.error(err)

    @commands.command(name='activity', description='Sets bot activity')
    @util.default_command(param_filter=r'^ *(.+?) *$', thesaurus={'r': 'random', 'rand': 'random', 'p': 'playing', 'play': 'playing', 'w': 'watching', 'watch': 'watching', 'l': 'listening', 'listen': 'listening', 'c': 'competing', 'comp': 'competing'})
    @util.summarized()
    @util.dev_only()
    async def activity(self, ctx: commands.Context, flags: list[str], vars: dict, params: list[str]) -> util.Summary:
        summary = util.Summary(ctx)

        # Check if activity is provided
        if not params and 'random' not in flags:
            summary.set_header('No activity or applicable flags provided')
            summary.set_field('Usage', f'`{ctx.prefix}activity <activity | --all> [--playing | --watching | --listening | --competing] [--verbose | --quiet]`\nUse `{ctx.prefix}help {ctx.command}` for more information.')
            log.error('No activity or flags provided')
            return summary

        if vars:
            variables = ', '.join([f'{key} = "{value}"' for key, value in vars.items()])
            log.warning(f'Redundant variables found: {variables}')
            summary.set_field('Redundant variables', f'This function does not accept variables, yet it found these: {variables}.')

        # Check if random activity is requested
        if 'random' in flags:
            log.debug(f'Following random branch for {ctx.prefix}{ctx.command}')
            await self.random_status()
            summary.set_header('Random activity selected')
            log.info('Random activity selected')
            return summary

        # Set activity
        if 'competing' in flags:
            activity_type = discord.ActivityType.competing
        elif 'watching' in flags:
            activity_type = discord.ActivityType.watching
        elif 'listening' in flags:
            activity_type = discord.ActivityType.listening
        else:
            activity_type = discord.ActivityType.playing

        await self.bot.change_presence(activity=discord.Activity(type=activity_type, name=params[0]))

        summary.set_header('New activity set')
        summary.set_field('New activity', params[0])
        log.info(f'Activity set to `{params[0]}`')
        return summary