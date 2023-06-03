
import asyncio
import logging
from os import getenv
from os.path import basename

import discord
from discord.ext import commands
from dotenv import load_dotenv
from pony.orm import db_session

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
        self.steam = None
        self.steam = steam.Client(getenv('STEAM_TOKEN'))

    @commands.group(name='ping', description='Better ping utility', invoke_without_command=True)
    @util.default_command()
    async def ping(self, ctx: commands.Context, flags: list[str], params: list[str]) -> None:
        pass
    
    @ping.command(name='setup', description='Ping setup')
    @util.default_command(thesaurus={'f': 'force', 'q': 'quiet', 'v': 'verbose'})
    @util.summarized()
    async def setup(self, ctx: commands.Context, flags: list[str], params: list[str]) -> discord.Embed:

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

            # Check if user already has a linked Steam account
            if db_user.steam_id:

                # Check if override is forced
                if 'force' in flags:
                    db_user.steam_id = steam_user.id64
                    log.info(f'Succesfully overrode Steam account to `{steam_user.name}` ({steam_user.id64}) for user `{ctx.author.name}` ({ctx.author.id})')

                # Prompt user with override
                else:

                    class VerifySteamOverride(discord.ui.View):
                        def __init__(self, *args, **kwargs) -> None:
                            super().__init__(timeout=60, disable_on_timeout=True, *args, **kwargs)
                            self.input = asyncio.Event()

                        async def await_input(self) -> None:
                            await self.input.wait()

                        # Override Steam account
                        @discord.ui.button(label='Override', style=discord.ButtonStyle.green, emoji='📝')
                        async def override(self, _, interaction: discord.Interaction) -> None:
                            with db_session:
                                db_user = User.get(discord_id=ctx.author.id) 
                                db_user.steam_id = steam_user.id64
                            
                            log.info(f'Succesfully overrode Steam account to `{steam_user.name}` ({steam_user.id64}) for user `{ctx.author.name}` ({ctx.author.id})')
                            await interaction.response.defer()
                            self.input.set()

                        # Abort override
                        @discord.ui.button(label='Abort', style=discord.ButtonStyle.red, emoji='👶')
                        async def abort(self, _, interaction: discord.Interaction) -> None:
                            log.info(f'User `{ctx.author.name}` ({ctx.author.id}) aborted Steam account override')
                            await interaction.response.defer()
                            self.input.set()

                    view = VerifySteamOverride()
                    log.debug(f'User `{ctx.author.name}` ({ctx.author.id}) already has linked Steam account')
                    await reply.edit(content='You already have a linked Steam account. Do you want to override the old account, or keep it?', view=view)
                    await view.await_input()

            # Link Steam account
            else:
                db_user.steam_id = steam_user.id64
                log.info(f"Succesfully linked Steam account `{steam_user.name}` ({steam_user.id64}) to user `{ctx.author.name}` ({ctx.author.id})")

        with db_session:

            # If Steam account was linked, update ping subscriptions
            status, summary = '', ''
            if db_user.steam_id:
                await reply.edit(content='DoSing the Steam API...', embed=None, view=None)
                status = f'Sucessfully linked Steam account `{steam_user.name}` to user `{ctx.author.name}`'
                for game in steam_user.games:
                    if not PingGroup.exists(steam_id=game.id):
                        game.unlazify()
                        PingGroup(name=game.name, steam_id=game.id)
                        log.info(f'Created ping `{game.name}` ({game.id})')
                    summary += f'Subscribed to ping `{game.name}`\n'
                    log.info(f'Subscribed user `{ctx.author.name}` ({ctx.author.id}) to ping `{game.name}` ({game.id})')

            else:
                status  = 'User aborted Steam account setup'
                summary = 'No subscriptions added.'

            # Give summary
            embed = util.default_embed(self.bot, 'Summary', status)
            embed.add_field(name='Subscriptions', value=summary)

            if 'quiet' not in flags:
                if 'verbose' in flags:
                    await reply.edit(content=None, embed=embed, view=None)
                else:
                    await reply.edit(content=status, view=None)
            return embed