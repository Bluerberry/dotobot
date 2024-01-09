
import asyncio
import logging
import os
import random
from os.path import basename

import discord
import dotenv
import pony.orm as pony
from discord.ext import commands

import lib.entities as entities
import lib.steam as steam
import lib.utility.util as util


# ---------------------> Logging setup


name = basename(__file__)[:-3]
log = logging.getLogger(name)


# ---------------------> Environment setup


dotenv.load_dotenv()


# ---------------------> UI classes


class SelectPingGroup(discord.ui.Select):
    def __init__(self, parent: discord.ui.View, options: list[entities.PingGroup], *args, **kwargs) -> None:
        super().__init__(
            placeholder='Select a ping group',
            options=[discord.SelectOption(label=option.name, value=option) for option in options],
            *args, **kwargs
        )

        self.parent = parent

    async def callback(self, interaction: discord.Interaction) -> None:

         # Only authorised users can interact
        if interaction.user != self.parent.authorised_user:
            await interaction.response.send_message('You are not authorised to do that.', ephemeral=True)
            return

        await interaction.response.defer()
        self.parent.result = self.values[0]
        self.parent.resolved.set()

class VaguePingGroup(discord.ui.View):
    def __init__(self, authorised_user: discord.User, options: list[entities.PingGroup], *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.authorised_user = authorised_user
        self.resolved = asyncio.Event()
        self.result = None

        # Create select menu
        select = SelectPingGroup(self, options)
        self.add_item(select)

    async def await_resolution(self) -> None | entities.PingGroup:
        await self.resolved.wait()
        self.disable_all_items()
        return self.result

    @discord.ui.button(label='Abort', style=discord.ButtonStyle.red, emoji='👶', row=1)
    async def abort(self, _, interaction: discord.Interaction) -> None:

        # Only authorised users can interact
        if interaction.user != self.authorised_user:
            await interaction.response.send_message('You are not authorised to do that.', ephemeral=True)
            return

        await interaction.response.defer()
        self.resolved.set()


# ---------------------> Ping cog


def setup(bot: commands.Bot) -> None:
    with pony.db_session:
        if entities.Extension.exists(name=name):
            extension = entities.Extension.get(name=name)
            extension.active = True

        else:
            entities.Extension(name=name, active=True)

    bot.add_cog(Ping(bot))
    log.info(f'Extension has been created: {name}')

def teardown(bot: commands.Bot) -> None:
    with pony.db_session:
        extension = entities.Extension.get(name=name)
        extension.active = False

    log.info(f'Extension has been destroyed: {name}')

class Ping(commands.Cog, name=name, description='Better ping utility'):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.steam = steam.Client(os.getenv('STEAM_TOKEN'))

    async def update_pings(self, summary: util.Summary | None = None) -> None:
        with pony.db_session:

            # Fetch new Steam data and update ping groups
            for db_user in entities.User.select(lambda db_user: db_user.steam_id):
                steam_user = self.steam.getUser(db_user.steam_id)

                # Check if Steam profile is private
                if steam_user.private:
                    log.warning(f'User `{ await self.bot.fetch_user(db_user.discord_id).name }` ({db_user.discord_id}) has their Steam library on private')
                    continue

                # Update ping groups
                new = 0
                for game in steam_user.games:
                    if not entities.PingGroup.exists(steam_id=game.id):
                        try:
                            game.unlazify()

                        except steam.errors.GameNotFoundError:
                            log.warning(f'No game with id ({game.id}) could be found in the Steam store')
                            continue

                        # Create new ping group
                        try:
                            entities.PingGroup(name=game.name, steam_id=game.id)
                            log.info(f'Created ping group `{game.name}` ({game.id})')
                            new += 1

                        except pony.core.CacheIndexError:
                            log.warn(f'Failed to create ping group with duplicate name or SteamID')

                if summary and new:
                    summary.set_field('New ping groups', f'Created {new} new ping group(s). For specifics, consult the logs.')

    async def find_pinggroup(self, query: str, dialog: util.Dialog, summary: util.Summary) -> int | None:

        # Search ping groups
        with pony.db_session:
            options = pony.select(util.SearchItem(pg, pg.name) for pg in entities.PingGroup)
            conclusive, results = util.fuzzy_search(options, query)

            if not results:
                log.error('No ping groups were found, search returned nothing')
                summary.set_header('No ping groups found')
                return

            # Results were conclusive
            if conclusive:
                pingGroup = results[0].item
                log.debug(f'Search results were conclusive, found ping group `{pingGroup.name}`')
                return pingGroup.id

            # Results weren't conclusive, send VaguePingGroup menu
            else:
                log.debug(f'Search results were inconclusive')
                view = VaguePingGroup(dialog.ctx.author, [result.item for result in results[:5]])
                await dialog.set('Search results were inconclusive! Did you mean any of these ping groups?', view=view)
                pingGroup = await view.await_resolution()

                # Parse result
                if not pingGroup:
                    log.warning(f'User `{dialog.ctx.author.name}` ({dialog.ctx.author.id}) aborted ping command.')
                    summary.set_header('ping command was aborted')
                    return

                log.debug(f'User chose `{pingGroup.name} from inconclusive search results')
                return pingGroup.id


    # ---------------------> Commands


    @commands.group(name='ping', description='Better ping utility', invoke_without_command=True)
    @util.default_command(param_filter=r'^ *(.+?) *$')
    @util.summarized()
    async def ping(self, ctx: commands.Context, flags: list[str], vars: dict, params: list[str]) -> util.Summary:
        summary = util.Summary(ctx)
        dialog = util.Dialog(ctx)

        # Check params
        if not params:
            summary.set_header('No parameters given')
            summary.set_field('Usage', f'`{ctx.prefix}ping <ping group> [--quiet | --verbose]`\nUse `{ctx.prefix}help status` for more information.')
            log.warn(f'No parameters given')
            await dialog.cleanup()
            return summary

        if vars:
            variables = ', '.join([f'{key} = "{value}"' for key, value in vars.items()])
            log.warning(f'Redundant variables found: {variables}')
            summary.set_field('Redundant variables', f'This function does not accept variables, yet it found these: {variables}.')

        # Update ping groups
        if 'quiet' not in flags:
            await dialog.set('DoSsing the Steam API...')
        await self.update_pings(summary)

        with pony.db_session:

            # Find ping group
            db_pingGroup = await self.find_pinggroup(params[0], dialog, summary)
            if not db_pingGroup:
                await dialog.cleanup()
                return summary

            # Find explicit subscribers
            subscribers = list(entities.User.select(lambda db_user: db_pingGroup.id in db_user.whitelisted_pings))

            # Find implicit subscribers
            if db_pingGroup.steam_id:
                for db_user in entities.User.select(lambda db_user: db_user.steam_id):
                    if db_pingGroup.id not in db_user.blacklisted_pings and db_user.discord_id not in subscribers:
                        steam_user = self.steam.getUser(db_user.steam_id)
                        if db_pingGroup.steam_id in [game.id for game in steam_user.games]:
                            subscribers.append(db_user)

            # Build and send ping message
            discord_users = [await self.bot.fetch_user(subscriber.discord_id) for subscriber in subscribers]
            message = random.choice([
                f'Hear ye, hear ye! Thou art did request to attend the court of {db_pingGroup.name}.\n',
                f'Get in loser, we\'re going to do some {db_pingGroup.name}.\n',
                f'The definition of insanity is launching {db_pingGroup.name} and expecting success. Let\'s go insane.\n',
                f'Whats more important, working on your future or joining {db_pingGroup.name}? Exactly.\n',
                f'The ping extention wasted weeks of my life, so thank you for using it. Lets play {db_pingGroup.name}!\n',
                f'Vamos a la {db_pingGroup.name}, oh ohhhhhhhh yeah!\n',
                f'Inspiratie is voor de inspiratielozen. Something something {db_pingGroup.name}.\n'
            ]) + ' '.join([user.mention for user in discord_users])

            await dialog.add(message, view=None, mention_author=False)

        summary.send_on_return = False
        summary.set_header('Successfully sent out ping')
        summary.set_field('Subscribers', '\n'.join([user.name for user in discord_users]))
        await dialog.cleanup()
        return summary

    @ping.command(name='setup', description='Ping setup')
    @util.default_command(param_filter=r'^ *(\d+) *$', thesaurus={'f': 'force'})
    @util.summarized()
    async def setup(self, ctx: commands.Context, flags: list[str], vars: dict, params: list[str]) -> util.Summary:
        summary = util.Summary(ctx)
        dialog = util.Dialog(ctx)

        # Check params
        if not params:
            summary.set_header('No parameters given')
            summary.set_field('Usage', f'`{ctx.prefix}ping setup <steam ID64> [--force] [--quiet | --verbose]`\nUse `{ctx.prefix}help status` for more information.')
            log.warn(f'No parameters given')
            await dialog.cleanup()
            return summary

        if vars:
            variables = ', '.join([f'{key} = "{value}"' for key, value in vars.items()])
            log.warning(f'Redundant variables found: {variables}')
            summary.set_field('Redundant variables', f'This function does not accept variables, yet it found these: {variables}.')

        # Validate SteamID
        try:
            if 'quiet' not in flags:
                await dialog.set('DoSsing the Steam API...')
            steam_user = self.steam.getUser(id64=params[0])

        except steam.errors.UserNotFoundError:
            summary.set_header('Invalid SteamID')
            summary.set_field('ValueError', f'SteamID `{params[0]}` could not be found. Make sure you provide your Steam ID64, found in your profile url.')
            log.warn(f'Invalid SteamID: `{params[0]}`')
            await dialog.cleanup()
            return summary

        # Link Steam account
        with pony.db_session:
            db_user = entities.User.get(discord_id=ctx.author.id)

            # Check if there already is a SteamID registered to this user
            if db_user.steam_id and 'force' not in flags:
                log.debug(f'User `{ctx.author.name}` ({ctx.author.id}) already has linked Steam account')

                # Prompt with override
                view = util.ContinueCancelMenu(ctx.author)
                await dialog.set('You already have a linked Steam account. Do you want to override the old account, or keep it?', view=view)
                result = await view.await_response()

                # Cleanup
                if not result:
                    log.info(f'User `{ctx.author.name}` ({ctx.author.id}) aborted ping setup')
                    summary.set_field('Subscriptions', 'No subscriptions added.')
                    summary.set_header('User aborted ping setup')
                    await dialog.cleanup()
                    return summary

            # Link Steam account
            db_user.steam_id = steam_user.id64
            if 'quiet' not in flags:
                await dialog.set('DoSsing the Steam API...', view=None)
            await self.update_pings(summary)

        # Update log and summary
        if steam_user.private:
            summary.set_field('New Subscriptions', 'No subscriptions added, Steam profile is set to private. When you set your profile to public you will be automatically subscribed to all games in your library.')
        else:
            summary.set_field('New Subscriptions', 'Steam library added to subscribed ping groups!')

        summary.set_header(f'Sucessfully linked Steam account `{steam_user.name}` to user `{ctx.author.name}`')
        log.info(f'Succesfully linked Steam account `{steam_user.name}` ({steam_user.id64}) to user `{ctx.author.name}` ({ctx.author.id})')
        await dialog.cleanup()
        return summary

    @ping.command(name='subscribe', description='Subscribe to a ping group')
    @util.default_command(param_filter=r'^ *(.+?) *$')
    @util.summarized()
    async def subscribe(self, ctx: commands.Context, flags: list[str], vars: dict, params: list[str]) -> util.Summary:
        summary = util.Summary(ctx)
        dialog = util.Dialog(ctx)

        # Check params
        if not params:
            summary.set_header('No parameters given')
            summary.set_field('Usage', f'`{ctx.prefix}ping subscribe <ping group> [--quiet | --verbose]`\nUse `{ctx.prefix}help status` for more information.')
            log.warn(f'No parameters given')
            await dialog.cleanup()
            return summary

        if vars:
            variables = ', '.join([f'{key} = "{value}"' for key, value in vars.items()])
            log.warning(f'Redundant variables found: {variables}')
            summary.set_field('Redundant variables', f'This function does not accept variables, yet it found these: {variables}.')

        # Update ping groups
        if 'quiet' not in flags:
            await dialog.set('DoSsing the Steam API...')
        await self.update_pings(summary)

        # Subscribe to ping group
        with pony.db_session:

            # Find ping group
            db_user = entities.User.get(discord_id=ctx.author.id)
            db_pingGroup = await self.find_pinggroup(params[0], dialog, summary)
            if not db_pingGroup:
                await dialog.cleanup()
                return summary

            # Check if user is manually subscribed
            if db_pingGroup.id in db_user.whitelisted_pings:
                log.warning(f'User `{ctx.author.name}` ({ctx.author.id}) already subscribed to ping group `{db_pingGroup.name}` ({db_pingGroup.id})')
                return

            # Check if user is automatically subscribed
            if db_pingGroup.steam_id and db_user.steam_id:
                steam_user = self.steam_client.getUser(db_user.steam_id)
                if db_pingGroup.steam_id in [game.id for game in steam_user.games]:
                    log.warning(f'User `{ctx.author.name}` ({ctx.author.id}) already subscribed to ping group `{db_pingGroup.name}` ({db_pingGroup.id})')
                    return

            # Subscribe user to ping group
            db_user.whitelisted_pings.append(db_pingGroup.id)
            if db_pingGroup.id in db_user.blacklisted_pings:
                db_user.blacklisted_pings.remove(db_pingGroup.id)

            # Cleanup
            log.info(f'User `{self.ctx.author.name}` ({self.ctx.author.id}) subscribed to ping group `{db_pingGroup.name}` ({db_pingGroup.id})')
            summary.set_header(f'Succesfully subscribed to ping group `{db_pingGroup.name}`')
            await dialog.cleanup()
            return summary

    @ping.command(name='unsubscribe', description='Unsubscribe from a ping group')
    @util.default_command(param_filter=r'^ *(.+?) *$')
    @util.summarized()
    async def unsubscribe(self, ctx: commands.Context, flags: list[str], vars: dict, params: list[str]) -> util.Summary:
        summary = util.Summary(ctx)
        dialog = util.Dialog(ctx)

        # Check params
        if not params:
            summary.set_header('No parameters given')
            summary.set_field('Usage', f'`{ctx.prefix}ping unsubscribe <ping group> [--quiet | --verbose]`\nUse `{ctx.prefix}help status` for more information.')
            log.warn(f'No parameters given')
            await dialog.cleanup()
            return summary

        if vars:
            variables = ', '.join([f'{key} = "{value}"' for key, value in vars.items()])
            log.warning(f'Redundant variables found: {variables}')
            summary.set_field('Redundant variables', f'This function does not accept variables, yet it found these: {variables}.')

        # Update ping groups
        if 'quiet' not in flags:
            await dialog.set('DoSsing the Steam API...')
        await self.update_pings(summary)

        # Subscribe to ping group
        with pony.db_session:

            # Find ping group
            unsubscribed = False
            db_user = entities.User.get(discord_id=ctx.author.id)
            db_pingGroup = await self.find_pinggroup(params[0], dialog, summary)
            if not db_pingGroup:
                await dialog.cleanup()
                return summary

            # Check if user is manually subscribed
            if db_pingGroup.id in db_user.whitelisted_pings:
                db_user.whitelisted_pings.remove(db_pingGroup.id)
                log.info(f'User `{self.ctx.author.name}` ({self.ctx.author.id}) unsubscribed from ping group `{db_pingGroup.name}` ({db_pingGroup.id})')
                summary.header(f'User succesfully unsubscribed from `{db_pingGroup.name}`')
                unsubscribed = True

            # Check if user is automatically subscribed
            if db_pingGroup.steam_id and db_user.steam_id:
                steam_user = self.steam_client.getUser(db_user.steam_id)
                if db_pingGroup.steam_id in [game.id for game in steam_user.games]:
                    db_user.blacklisted_pings.append(db_pingGroup.id)
                    log.info(f'User `{self.ctx.author.name}` ({self.ctx.author.id}) blacklisted ping group `{db_pingGroup.name}` ({db_pingGroup.id})')
                    summary.header(f'User succesfully blacklisted `{db_pingGroup.name}`')
                    unsubscribed = True

            # Check if user was subscribed in the first place
            if not unsubscribed:
                log.warning(f'User `{self.ctx.author.name}` ({self.ctx.author.id}) was never subscribed ping group `{db_pingGroup.name}` ({db_pingGroup.id})')
                summary.header(f'User was never subscribed to `{db_pingGroup.name}`')

            await dialog.cleanup()
            return summary

    @ping.command(name='add', description='Add a ping group')
    @util.default_command(param_filter=r'^ *(.+?) *$')
    @util.summarized()
    async def add(self, ctx: commands.Context, flags: list[str], vars: dict, params: list[str]) -> util.Summary:
        summary = util.Summary(ctx)
        dialog = util.Dialog(ctx)

        # Check params
        if not params:
            log.error(f'No parameters given')
            summary.set_header('No parameters given')
            summary.set_field('ValueError', 'User provided no parameters, while command usage dictates `$ping add [name] --[flags]`')
            await dialog.cleanup()
            return summary

        if vars:
            variables = ', '.join([f'{key} = "{value}"' for key, value in vars.items()])
            log.warning(f'Redundant variables found: {variables}')
            summary.set_field('Redundant variables', f'This function does not accept variables, yet it found these: {variables}.')

        # Update pings
        if 'quiet' not in flags:
            await dialog.set('DoSsing the Steam API...')
        await self.update_pings(summary)

        # Search ping groups
        with pony.db_session:
            options = pony.select(pg.name for pg in entities.PingGroup)
            conclusive, results = util.fuzzy_search(options, params[0])

            # If conclusive, there is another ping group with a conflicting name
            if conclusive:
                log.warn(f'Failed to create ping group by name of `{params[0]}` due to conflicting ping group `{results[0]["name"]}`')
                summary.set_header('Failed to create ping group')
                summary.set_field('ConflictingNameError', f'There already is a similar ping group with the name `{results[0]["name"]}`. If your new ping group targets a different audience, try giving it a different name. Stupid.')
                await dialog.cleanup()
                return summary

            # Create new ping group
            pingGroup = entities.PingGroup(name=params[0])
            pony.commit()
            log.info(f'Created new ping group `{pingGroup.name}` ({pingGroup.id}) at the request of user `{ctx.author.name}` ({ctx.author.id})')

        summary.set_header(f'Successfully created ping group `{pingGroup.name}`')
        await dialog.cleanup()
        return summary

    @ping.command(name='delete', description='Delete a ping group')
    @util.default_command(param_filter=r'^ *(.+?) *$')
    @util.summarized()
    @util.dev_only()
    async def delete(self, ctx: commands.Context, flags: list[str], vars: dict, params: list[str]) -> util.Summary:
        summary = util.Summary(ctx)
        dialog = util.Dialog(ctx)

        # Check params
        if not params:
            summary.set_header('No parameters given')
            summary.set_field('Usage', f'`{ctx.prefix}ping add <ping group> [--quiet | --verbose]`\nUse `{ctx.prefix}help status` for more information.')
            log.warn(f'No parameters given')
            await dialog.cleanup()
            return summary

        if vars:
            variables = ', '.join([f'{key} = "{value}"' for key, value in vars.items()])
            log.warning(f'Redundant variables found: {variables}')
            summary.set_field('Redundant variables', f'This function does not accept variables, yet it found these: {variables}.')

        # Update pings
        if 'quiet' not in flags:
            await dialog.set('DoSsing the Steam API...')
        await self.update_pings(summary)

        with pony.db_session:

            # Find ping group
            db_pingGroup = await self.find_pinggroup(params[0], dialog, summary)
            if not db_pingGroup:
                await dialog.cleanup()
                return summary

            # Check if ping group is implicit
            if db_pingGroup.steam_id:
                summary.set_header('Failed to delete implicit ping group')
                summary.set_field('ImplicitPingGroupError', f'Ping group `{db_pingGroup.name}` is implicitly created from a Steam library, and thus cannot be deleted.')
                log.warn(f'Ping group `{db_pingGroup.name}` is implicitly created from a Steam library, and thus cannot be deleted.')
                await dialog.cleanup()
                return summary

            # Delete ping group
            for db_user in pony.select(db_user for db_user in entities.User):
                if db_pingGroup.id in db_user.whitelisted_pings:
                    db_user.whitelisted_pings.remove(db_pingGroup.id)

                if db_pingGroup.id in db_user.blacklisted_pings:
                    db_user.blacklisted_pings.remove(db_pingGroup.id)

            log.info(f'Successfully deleted ping group `{db_pingGroup.name}` ({db_pingGroup.id})')
            summary.set_header(f'Successfully deleted ping group `{db_pingGroup.name}`')
            db_pingGroup.delete()
            await dialog.cleanup()
            return summary