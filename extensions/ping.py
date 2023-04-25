
import logging
from os.path import basename

import discord
from discord.ext import commands
from pony.orm import db_session
from steam.steamid import SteamID
import steamfront

import util
from entities import User, Ping

# ---------------------> Logging setup

name = basename(__file__)[:-2]
log = logging.getLogger(name)

# ---------------------> Steam setup

steam = steamfront.Client()

# ---------------------> Ping cog

def setup(bot: commands.Bot) -> None:
    bot.add_cog(Ping(bot))
    log.info(f'Extension has been created: {name}')

def teardown(bot: commands.Bot) -> None:
    log.info(f'Extension has been destroyed: {name}')

class Ping(commands.Cog, name = name, description = 'Better ping utility'):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.group(name='ping', description='Better ping utility', invoke_without_command=True)
    @util.default_command()
    async def ping(self, ctx: commands.Context, flags: list[str], params: list[str]) -> None:
        await ctx.send('No subcommand invoked! Use `$help ping` for usage.') # TODO implement $help ping
    
    @ping.command(name='setup', description='Ping setup')
    @util.default_command()
    async def setup(self, ctx: commands.Context, flags: list[str], params: list[str]) -> None:
        class PingSetup(discord.ui.View):
            def __init__(self, *args, **kwargs) -> None:
                super().__init__(timeout=10, disable_on_timeout=True, *args, **kwargs)

            # Link Steam account
            @discord.ui.button(label='Link Steam', style=discord.ButtonStyle.blurple, emoji='🎮')
            async def link(self, _, interaction: discord.Interaction) -> None:
                class LinkSteam(discord.ui.Modal):
                    def __init__(self, *args, **kwargs) -> None:
                        super().__init__(title='Link Steam', *args, **kwargs)
                        self.add_item(discord.ui.InputText(label='Steam ID'))

                    async def callback(self, interaction: discord.Interaction) -> None:

                        # Validate Steam ID
                        translator = SteamID(self.children[0].value)
                        if not translator.is_valid():
                            log.warn(f'Failed to validate Steam ID `{self.children[0].value}` for user `{ctx.author.name}` ({ctx.author.id})')
                            await interaction.response.send_message('Failed to validate Steam ID...')
                            return
                        target_id = translator.as_64

                        # Check if user already has a linked Steam account
                        with db_session:
                            db_user = User.get(discord_id=ctx.author.id)
                            if db_user.steam_id:
                                class VerifySteamOverride(discord.ui.View):
                                    def __init__(self, *args, **kwargs) -> None:
                                        super().__init__(timeout=60, disable_on_timeout=True, *args, **kwargs)

                                    # Override Steam account
                                    @discord.ui.button(label='Override', style=discord.ButtonStyle.green, emoji='📝')
                                    async def override(self, _, interaction: discord.Interaction) -> None:
                                        with db_session:
                                            db_user = User.get(discord_id=ctx.author.id)
                                            db_user.steam_id = target_id
                                            log.info(f'Succesfully overrode Steam account to `{target_id}` for user `{ctx.author.name}` ({ctx.author.id})')
                                            await interaction.response.edit_message(content='Sucessfully linked Steam account!', view=None)

                                            # Update Pings
                                            for app in steam.getUser(id64=target_id).apps:
                                                if not Ping.exists(steam_id=app.appid):
                                                    Ping(name=app.name, steam_id=app.appid)


                                    # Abort override
                                    @discord.ui.button(label='Abort', style=discord.ButtonStyle.red, emoji='👶')
                                    async def abort(self, _, interaction: discord.Interaction) -> None:
                                        log.debug(f'User `{ctx.author.name}` ({ctx.author.id}) aborted Steam account override')
                                        await interaction.response.edit_message(content='You aborted Steam account override.', view=None)

                                log.debug(f'User `{ctx.author.name}` ({ctx.author.id}) already has linked Steam account')
                                await interaction.response.send_message('You already have a linked Steam account. Do you want to override the old account, or keep it?', view=VerifySteamOverride())
                                return

                            # Link Steam account
                            db_user.steam_id = target_id
                            log.info(f"Succesfully linked Steam account `{target_id}` to user `{ctx.author.name}` ({ctx.author.id})")
                            await interaction.response.send_message('Sucessfully linked Steam account!')

                            # Update Pings
                            for app in steam.getUser(id64=target_id).apps:
                                if not Ping.exists(steam_id=app.appid):
                                    Ping(name=app.name, steam_id=app.appid)

                # Launch LinkSteam Modal
                log.debug(f'User `{ctx.author.name}` ({ctx.author.id}) is linking a Steam account')
                await interaction.response.send_modal(LinkSteam())

            @discord.ui.button(label='Subscribe', style=discord.ButtonStyle.grey, emoji='📬')
            async def subscribe(self, button, interaction: discord.Interaction) -> None:
                await interaction.response.send_modal(Subscribe()) # TODO implement subscribe menu

            @discord.ui.button(label='Unsubscribe', style=discord.ButtonStyle.grey, emoji='📭')
            async def unsubscribe(self, button, interaction: discord.Interaction) -> None:
                await interaction.response.send_modal(Unsubscribe()) # TODO implement unsubscribe menu

        with db_session:
            if not User.exists(discord_id=ctx.author.id):
                log.error(f'User `{ctx.author.name}` ({ctx.author.id}) not in database')
                await ctx.send('You are not in the database! Contact an admin.')
                return

        await ctx.author.send('Welcome to the Ping setup menu! Here you can sub- and unsubscribe from Pings, and link your Steam account. Any games in your Steam library will automatically be added to your subscribed Pings. For all Ping related commands, use `$help ping`.', view=PingSetup()) # TODO implement $help ping
        await ctx.reply('The Ping setup menu has been sent to your DM\'s.', mention_author=False)