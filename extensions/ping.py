
import asyncio
import logging
from os import getenv
from os.path import basename

import discord
from discord.ext import commands
from dotenv import load_dotenv
from pony.orm import db_session, select

import steam
import util
from entities import PingGroup, User

# ---------------------> Logging setup

name = basename(__file__)[:-3]
log = logging.getLogger(name)

# ---------------------> Environment setup

load_dotenv()
    
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

    @commands.group(name='ping', description='Better ping utility', invoke_without_command=True)
    @util.default_command(thesaurus={'q': 'quiet', 'v': 'verbose'})
    @util.summarized()
    async def ping(self, ctx: commands.Context, flags: list[str], params: list[str]) -> discord.Embed:
                
        # Check params
        if len(params) < 1:
            log.error(f'No parameters given')
            embed = util.default_embed(self.bot, 'Summary', 'No parameters given')
            embed.add_field(name='ValueError', value=f'User provided no parameters, while command usage dictates `$ping [query] -[flags]`')

            if 'quiet' not in flags:
                if 'verbose' in flags:
                    await ctx.reply(embed=embed)
                else:
                    await ctx.reply('No parameters given')
            return embed

        # Fetch new Steam data and update ping groups
        with db_session:
            for db_user in User.select(lambda db_user: db_user.steam_id):
                steam_user = self.steam.getUser(db_user.steam_id)
                
                # Check if Steam profile is private
                if steam_user.private:
                    log.warning(f'User `{ await self.bot.fetch_user(db_user.discord_id).name }` ({db_user.discord_id}) has their Steam library on private')
                    continue
                
                # Update ping groups
                for game in steam_user.games:
                    if not PingGroup.exists(steam_id=game.id):
                        try:
                            game.unlazify()
                        except steam.errors.GameNotFound:
                            log.warning(f'No game with id ({game.id}) could be found in the Steam store')
                            continue

                        # Create new ping group
                        PingGroup(name=game.name, steam_id=game.id)
                        log.info(f'Created ping `{game.name}` ({game.id})')
        
        # Search ping groups
        with db_session:
            options = select(pg.name for pg in PingGroup)
            result = util.fuzzy_search(options, ' '.join(params))
            pingGroup = PingGroup.get(name=result[0]['name'])

            # Find subscribers
            subscribers = list(User.select(lambda db_user: pingGroup.id in db_user.whitelisted_pings))
            if pingGroup.steam_id != None:
                for db_user in User.select(lambda db_user: db_user.steam_id):

                    # Check if ping group is blacklisted
                    if pingGroup.id in db_user.blacklisted_pings:
                        continue

                    # Check if Steam profile is private
                    steam_user = self.steam.getUser(db_user.steam_id)
                    if steam_user.private:
                        log.warning(f'User `{ await self.bot.fetch_user(db_user.discord_id).name }` ({db_user.discord_id}) has their Steam library on private')
                        continue

                    # Check if ping group is in library
                    if pingGroup.steam_id in [game.id for game in steam_user.games] and db_user not in subscribers:
                        subscribers.append(db_user)

            message = ''
            for db_user in subscribers:
                discord_user = await self.bot.fetch_user(db_user.discord_id)
                message += f'{discord_user.mention} '
            await ctx.reply(message)

    @ping.command(name='setup', description='Ping setup')
    @util.default_command(thesaurus={'f': 'force', 'q': 'quiet', 'v': 'verbose'})
    @util.summarized()
    async def setup(self, ctx: commands.Context, flags: list[str], params: list[str]) -> discord.Embed:
        async def link(steam_user: steam.User, reply: discord.Message) -> discord.Embed:
            status, summary = '', ''

            with db_session:
                db_user = User.get(discord_id=ctx.author.id)
                db_user.steam_id = steam_user.id64

                if db_user.discord_id:
                    log.info(f'Succesfully overrode Steam account to `{steam_user.name}` ({steam_user.id64}) for user `{ctx.author.name}` ({ctx.author.id})')
                    status = f'Sucessfully overrode Steam account to `{steam_user.name}` for user `{ctx.author.name}`'
                else:
                    log.info(f"Succesfully linked Steam account `{steam_user.name}` ({steam_user.id64}) to user `{ctx.author.name}` ({ctx.author.id})")
                    status = f'Sucessfully linked Steam account `{steam_user.name}` to user `{ctx.author.name}`'

                # Update reply
                await reply.edit(content='DoSing the Steam API...', embed=None, view=None)

                # Check if steam profile is private
                if steam_user.private:
                    summary = 'No subscriptions added, Steam profile is set to private. When you set your profile to public you will be automatically subscribed to all games in your library.'
                    log.warning(f'User `{ctx.author.name}` ({ctx.author.id}) has their Steam library on private')

                # Update ping groups
                else:
                    for game in steam_user.games:
                        if not PingGroup.exists(steam_id=game.id):
                            try:
                                game.unlazify()
                            except steam.errors.GameNotFound:
                                continue

                            # Create new ping group
                            PingGroup(name=game.name, steam_id=game.id)
                            summary += f'Created, and subscribed to, new ping `{game.name}`\n'
                            log.info(f'Created ping `{game.name}` ({game.id})')

                        else:                   
                            summary += f'Subscribed to ping `{game.name}`\n'
                        log.info(f'Subscribed user `{ctx.author.name}` ({ctx.author.id}) to ping `{game.name}` ({game.id})')

            # Give summary
            embed = util.default_embed(self.bot, 'Summary', status)
            embed.add_field(name='Subscriptions', value=summary)

            if 'quiet' not in flags:
                if 'verbose' in flags:
                    await reply.edit(content=None, embed=embed, view=None)
                else:
                    await reply.edit(content=status, view=None)
            return embed
        
        # Check params
        if len(params) != 1:
            log.error(f'Bad parameters given: `{" ".join(params)}`')
            embed = util.default_embed(self.bot, 'Summary', 'Bad parameters given')
            embed.add_field(name='ValueError', value=f'User provided the following parameters:\n\t`{" ".join(params)}`\n\nWhile command usage dictates `$ping setup [SteamID] -[flags]`')

            if 'quiet' not in flags:
                if 'verbose' in flags:
                    await ctx.reply(embed=embed)
                else:
                    await ctx.reply('Bad parameters given')
            return embed

        # Validate SteamID
        try:
            reply = await ctx.reply('DoSing the Steam API...')
            steam_user = self.steam.getUser(id64=params[0])
        
        except steam.errors.UserNotFound:
            log.warn(f'Invalid SteamID: `{params[0]}`')
            embed = util.default_embed(self.bot, 'Summary', 'Invalid SteamID')
            embed.add_field(name='ValueError', value=f'SteamID `{params[0]}` could not be found. Make sure you provide your Steam ID64, found in your profile url.')

            if 'quiet' not in flags:
                if 'verbose' in flags:
                    await reply.edit(content=None, embed=embed)
                else:
                    await reply.edit(content='Invalid SteamID')
            return embed
        
        # Link Steam account
        with db_session:
            db_user = User.get(discord_id=ctx.author.id)

            # Prompt with override if necissary
            if db_user.steam_id and 'force' not in flags:
                class VerifySteamOverride(discord.ui.View):
                    def __init__(self, bot: commands.Bot, *args, **kwargs) -> None:
                        super().__init__(*args, **kwargs)
                        self.input = asyncio.Event()
                        self.summary = None
                        self.bot = bot

                    # Blocks until any button has been pressed, then disables all items
                    async def await_completion(self) -> discord.Embed:
                        await self.input.wait()
                        self.disable_all_items()
                        return self.summary

                    # Override Steam account
                    @discord.ui.button(label='Override', style=discord.ButtonStyle.green, emoji='📝')
                    async def override(self, _, interaction: discord.Interaction) -> None:
                        await interaction.response.defer()

                        self.summary = await link(steam_user, reply)
                        self.input.set()

                    # Abort override
                    @discord.ui.button(label='Abort', style=discord.ButtonStyle.red, emoji='👶')
                    async def abort(self, _, interaction: discord.Interaction) -> None:
                        await interaction.response.defer()

                        log.info(f'User `{ctx.author.name}` ({ctx.author.id}) aborted Steam account override')
                        embed = util.default_embed(self.bot, 'Summary', 'User aborted Steam account override')
                        embed.add_field(name='Subscriptions', value='No subscriptions added.')

                        if 'quiet' not in flags:
                            if 'verbose' in flags:
                                await reply.edit(content=None, embed=embed, view=None)
                            else:
                                await reply.edit(content='User aborted Steam account override', view=None)                        

                        self.summary = embed
                        self.input.set()

                view = VerifySteamOverride(self.bot)
                log.debug(f'User `{ctx.author.name}` ({ctx.author.id}) already has linked Steam account')
                await reply.edit(content='You already have a linked Steam account. Do you want to override the old account, or keep it?', view=view)
                return await view.await_completion()

            # Link Steam account
            return await link(steam_user, reply)

            
        