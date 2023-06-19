
import asyncio
import logging
from os import getenv
from os.path import basename
from random import choice

import discord
from discord.ext import commands
from dotenv import load_dotenv
from pony.orm import db_session, select

import steam
import util
import entities


# ---------------------> Logging setup


name = basename(__file__)[:-3]
log = logging.getLogger(name)


# ---------------------> Environment setup


load_dotenv()


# ---------------------> UI components


class SubscribeButton(discord.ui.Button):
    def __init__(self, steam_client: steam.Client, command_ctx: commands.Context, db_pingGroup: entities.User, *args, **kwargs) -> None:
        super().__init__(style=discord.ButtonStyle.green, lable='Subscribe', emoji='📬' *args, **kwargs)
        self.steam_client: steam.Client = steam_client
        self.command_ctx: commands.Context = command_ctx
        self.db_pingGroup: entities.PingGroup = db_pingGroup

    async def callback(self, interaction: discord.Interaction) -> None:

        # Only the original command author can interact with this button
        if interaction.user != self.command_ctx.author:
            return
        await interaction.response.defer()

        with db_session:
            db_user: entities.User = entities.User.get(discord_id=self.command_ctx.author.id)

            # Check if user is manually subscribed
            if self.db_pingGroup.id in db_user.whitelisted_pings:
                log.warning(f'User `{self.command_ctx.author.name}` ({self.command_ctx.author.id}) already subscribed to Ping group `{self.db_pingGroup.name}` ({self.db_pingGroup.id})')
                return

            # Check if user is automatically subscribed
            if self.db_pingGroup.steam_id and db_user.steam_id:
                steam_user: steam.User = self.steam_client.getUser(db_user.steam_id)
                if self.db_pingGroup.steam_id in [game.id for game in steam_user.games]:
                    log.warning(f'User `{self.command_ctx.author.name}` ({self.command_ctx.author.id}) already subscribed to Ping group `{self.db_pingGroup.name}` ({self.db_pingGroup.id})')
                    return

            # Subscribe user to ping group
            db_user.blacklisted_pings.append(self.db_pingGroup.id)
            if self.db_pingGroup.id in db_user.blacklisted_pings:
                db_user.blacklisted_pings.remove(self.db_pingGroup.id)
            log.info(f'User `{self.command_ctx.author.name}` ({self.command_ctx.author.id}) subscribed to Ping group `{self.db_pingGroup.name}` ({self.db_pingGroup.id})')

class UnsubscribeButton(discord.ui.Button):
    def __init__(self, steam_client: steam.Client, command_ctx: commands.Context, db_pingGroup: entities.PingGroup, *args, **kwargs) -> None:
        super().__init__(style=discord.ButtonStyle.red, lable='Unsubscribe', emoji='📪' *args, **kwargs)
        self.steam_client: steam.Client = steam_client
        self.command_ctx: commands.Context = command_ctx
        self.db_pingGroup: entities.PingGroup = db_pingGroup

    async def callback(self, interaction: discord.Interaction):

        # Only the original command author can interact with this button
        if interaction.user != self.command_ctx.author:
            return
        await interaction.response.defer()

        with db_session:
            db_user: entities.User = entities.User.get(discord_id=self.command_ctx.author.id)
            unsubscribed: bool = False

            # Check if user is manually subscribed
            if self.db_pingGroup.id in db_user.whitelisted_pings:
                db_user.whitelisted_pings.remove(self.db_pingGroup.id)
                log.info(f'User `{self.command_ctx.author.name}` ({self.command_ctx.author.id}) unsubscribed from Ping group `{self.db_pingGroup.name}` ({self.db_pingGroup.id})')
                unsubscribed = True

            # Check if user is automatically subscribed
            if self.db_pingGroup.steam_id and db_user.steam_id:
                steam_user: steam.User = self.steam_client.getUser(db_user.steam_id)
                if self.db_pingGroup.steam_id in [game.id for game in steam_user.games]:
                    db_user.blacklisted_pings.append(self.db_pingGroup.id)
                    log.info(f'User `{self.command_ctx.author.name}` ({self.command_ctx.author.id}) blacklisted Ping group `{self.db_pingGroup.name}` ({self.db_pingGroup.id})')
                    unsubscribed = True

            # Check if user was subscribed in the first place
            if unsubscribed:
                log.warning(f'User `{self.command_ctx.author.name}` ({self.command_ctx.author.id}) was never subscribed Ping group `{self.db_pingGroup.name}` ({self.db_pingGroup.id})')

class PingGroupMenu(discord.ui.View):
    async def __init__(self, bot: commands.Bot, steam_client: steam.Client, command_ctx: commands.Context, db_pingGroup: entities.User, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.bot: commands.Bot = bot
        self.steam_client: steam.Client = steam_client
        self.command_ctx: commands.Context = command_ctx
        self.db_pingGroup: entities.PingGroup = db_pingGroup

        # Find subscribers
        with db_session:
            self.subscribers: list[entities.User] = list(entities.User.select(lambda db_user: db_pingGroup.id in db_user.whitelisted_pings))
            if db_pingGroup.steam_id != None:
                for db_user in entities.User.select(lambda db_user: db_user.steam_id):

                    # Check if ping group is blacklisted
                    if db_pingGroup.id in db_user.blacklisted_pings:
                        continue

                    # Check if Steam profile is private
                    steam_user = steam_client.getUser(db_user.steam_id)
                    if steam_user.private:
                        log.warning(f'User `{ await bot.fetch_user(db_user.discord_id).name }` ({db_user.discord_id}) has their Steam library on private')
                        continue

                    # Check if ping group is in library
                    if db_pingGroup.steam_id in [game.id for game in steam_user.games] and db_user not in self.subscribers:
                        self.subscribers.append(db_user)

        # Add (un)subscribe button
        if command_ctx.author.id in [db_user.id for db_user in self.subscribers]:
            self.add_item(UnsubscribeButton(steam_client, command_ctx, db_pingGroup))
        else:
            self.add_item(SubscribeButton(steam_client, command_ctx, db_pingGroup))

    # Override Steam account
    @discord.ui.button(label='Ping', style=discord.ButtonStyle.blurple, emoji='📨')
    async def ping(self, _, interaction: discord.Interaction) -> None:

        # Only the original command author can interact with this view
        if interaction.user != self.command_ctx.author:
            return
        await interaction.response.defer()

        message = choice([
            f'Hear ye, hear ye! Thou art did request to attend the court of {self.db_pingGroup.name}.\n',
            f'Get in loser, we\'re going to do some {self.db_pingGroup.name}.\n',
            f'The definition of insanity is launching {self.db_pingGroup.name} and expecting success. Let\'s go insane.\n',
            f'Whats more important, working on your future or joining {self.db_pingGroup.name}? Exactly.\n',
            f'The ping extention wasted weeks of my life, so thank you for using it. Lets play {self.db_pingGroup.name}!\n',
            f'Vamos a la {self.db_pingGroup.name}, oh ohhhhhhhh yeah!\n'
        ])

        message += ' '.join([await self.bot.fetch_user(db_user.discord_id).mention for db_user in self.subscribers])
        await self.command_ctx.reply(message)

class VerifySteamOverride(discord.ui.View):
    def __init__(self, summary: util.Summary | None = None, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.responded = asyncio.Event()
        self.result = None
        self.summary = summary

    # Blocks until any button has been pressed, then disables all items
    async def await_response(self) -> None:
        await self.responded.wait()
        self.disable_all_items()

    # Override Steam account
    @discord.ui.button(label='Override', style=discord.ButtonStyle.green, emoji='📝')
    async def override(self, _, interaction: discord.Interaction) -> None:
        await interaction.response.defer()

        self.result = True
        self.responded.set()

    # Abort override
    @discord.ui.button(label='Abort', style=discord.ButtonStyle.red, emoji='👶')
    async def abort(self, _, interaction: discord.Interaction) -> None:
        await interaction.response.defer()

        if self.summary:
            self.summary.setHeader('User aborted Steam account override')
            self.summary.setField('Subscriptions', 'No subscriptions added.')

        self.result = False
        self.responded.set()


# ---------------------> Ping cog


def setup(bot: commands.Bot) -> None:
    bot.add_cog(Ping(bot))
    log.info(f'Extension has been created: {name}')

def teardown(bot: commands.Bot) -> None:
    log.info(f'Extension has been destroyed: {name}')

class Ping(commands.Cog, name = name, description = 'Better ping utility'):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.steam = steam.Client(getenv('STEAM_TOKEN'))

    def find_subscribers(self, ping_id: int) -> list[int]:
        with db_session:

            # Find explicit subscribers
            pingGroup = entities.PingGroup.get(id=ping_id)
            subscribers = entities.User.select([db_user.discord_id for db_user in entities.User if pingGroup.id in db_user.whitelisted_pings])

            # Find implicit subscribers
            if pingGroup.steam_id:
                for db_user in entities.User.select(lambda db_user: db_user.steam_id):
                    if pingGroup.id not in db_user.blacklisted_pings and db_user.discord_id not in subscribers:
                        steam_user = self.steam.getUser(db_user.steam_id)
                        if pingGroup.steam_id in [game.id for game in steam_user.games]:
                            subscribers.append(db_user)

        return subscribers

    async def update_pings(self, summary: util.Summary | None = None) -> None:
        with db_session:

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
                        except steam.errors.GameNotFound:
                            log.warning(f'No game with id ({game.id}) could be found in the Steam store')
                            continue

                        # Create new ping group
                        entities.PingGroup(name=game.name, steam_id=game.id)
                        log.info(f'Created Ping Group `{game.name}` ({game.id})')
                        new += 1

                if summary:
                    summary.setField('New Ping Groups', f'Created {new} new Ping Group(s). For specifics, consult the logs.')


    # ---------------------> Commands


    @commands.group(name='ping', description='Better ping utility', invoke_without_command=True)
    @util.default_command(thesaurus={'q': 'quiet', 'v': 'verbose'})
    @util.summarized()
    async def ping(self, ctx: commands.Context, flags: list[str], params: list[str]) -> util.Summary:
        summary = util.Summary(ctx)

        # Check params
        if len(params) < 1:
            log.error(f'No parameters given')
            summary.setHeader('No parameters given')
            summary.setField('ValueError', 'User provided no parameters, while command usage dictates `$ping [query] -[flags]`')
            return summary

        # Update pings
        reply = await ctx.reply('DoSsing the Steam API...', embed=None, view=None)
        await self.update_pings(summary)

        # Search ping groups
        with db_session:
            options = select(pg.name for pg in entities.PingGroup)
            conclusive, results = util.fuzzy_search(options, ' '.join(params))

            # Results were conclusive
            if conclusive:
                pingGroup = entities.PingGroup.get(name=results[0]['name'])
                subscribers = self.find_subscribers(pingGroup.id)

                # Build and send Ping menu
                message = ''
                for db_user in subscribers:
                    discord_user = await self.bot.fetch_user(db_user.discord_id)
                    message += f'{discord_user.name}\n'

                embed = util.default_embed(self.bot, f'Ping group - {pingGroup.name}', 'This is a Ping group! You can ping all subscribers of this group, subscribe yourself or edit this ping!')
                embed.add_field(name='Subscribers', value=message)
                await reply.edit('', embed=embed, view=PingGroupMenu(self.bot, self.steam, ctx, pingGroup))

            # Results weren't conclusive
            else:

                # TODO add wrong result menu
                await ctx.reply('inconclusive results')

        await reply.delete()
        return summary


        # if results are conclusive
        #   goto wrong result menu
        # else
        #   goto main menu

        # Main menu
        #  - shows ping subscribers
        #  - ping button
        #  - subscribe/unsubscribe button
        #  - wrong result button

        # Wrong result menu
        #  - shows top 5 results
        #  - user choice is sent to main menu
        #  - nevermind button

    @ping.command(name='setup', description='Ping setup')
    @util.default_command(thesaurus={'f': 'force', 'q': 'quiet', 'v': 'verbose'})
    @util.summarized()
    async def setup(self, ctx: commands.Context, flags: list[str], params: list[str]) -> discord.Embed:
        summary = util.Summary(ctx)

        # Check params
        if len(params) != 1:
            log.error(f'Bad parameters given: `{" ".join(params)}`')
            summary.setHeader('Bad parameters Given')
            summary.setField('ValueError', f'User provided the following parameters:\n\t`{" ".join(params)}`\n\nWhile command usage dictates `$ping setup [SteamID] -[flags]`')
            return summary

        # Validate SteamID
        try:
            if 'quiet' not in flags:
                reply = await ctx.reply('DoSsing the Steam API...', embed=None, view=None)
            steam_user = self.steam.getUser(id64=params[0])

        except steam.errors.UserNotFound:
            log.warn(f'Invalid SteamID: `{params[0]}`')
            summary.setHeader('Invalid SteamID')
            summary.setField('ValueError', f'SteamID `{params[0]}` could not be found. Make sure you provide your Steam ID64, found in your profile url.')
            return summary

        # Link Steam account
        with db_session:
            db_user = entities.User.get(discord_id=ctx.author.id)

            # Check if there already is a SteamID registered to this user
            if db_user.steam_id and 'force' not in flags:
                view = VerifySteamOverride(summary)
                log.debug(f'User `{ctx.author.name}` ({ctx.author.id}) already has linked Steam account')

                # Prompt with override
                if 'quiet' in flags:
                    reply = await ctx.reply('You already have a linked Steam account. Do you want to override the old account, or keep it?', embed=None, view=view)
                else:
                    await reply.edit('You already have a linked Steam account. Do you want to override the old account, or keep it?', embed=None, view=view)
                await view.await_response()

                # Cleanup
                if not view.result:
                    await reply.delete()
                    return summary
                await reply.edit('DoSsing the Steam API...', embed=None, view=None)
                 
            # Update log and summary
            if db_user.steam_id:
                summary.setHeader(f'Sucessfully overrode Steam account to `{steam_user.name}` for user `{ctx.author.name}`')
                log.info(f'Succesfully overrode Steam account to `{steam_user.name}` ({steam_user.id64}) for user `{ctx.author.name}` ({ctx.author.id})')
            else:
                summary.setHeader(f'Sucessfully linked Steam account `{steam_user.name}` to user `{ctx.author.name}`')
                log.info(f"Succesfully linked Steam account `{steam_user.name}` ({steam_user.id64}) to user `{ctx.author.name}` ({ctx.author.id})")

            if steam_user.private:
                summary.setField('New Subscriptions', 'No subscriptions added, Steam profile is set to private. When you set your profile to public you will be automatically subscribed to all games in your library.')
            else:
                summary.setField('New Subscriptions', 'Steam library added to subscribed Ping Groups!')

            # Link Steam account
            db_user.steam_id = steam_user.id64

        # Cleanup
        await self.update_pings(summary)
        if reply in locals():
            await reply.delete()
        return summary
