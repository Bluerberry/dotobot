
import logging
from os.path import basename

import discord
from discord.ext import commands
from pony.orm import db_session
from steam.steamid import SteamID
from steamfront import client

from entities import User, Ping
import util

# ---------------------> Logging setup

name = basename(__file__)[:-2]
log = logging.getLogger(name)

# ---------------------> Steam setup

steam_client = client.Client()

# ---------------------> Example cog

def setup(bot: commands.Bot) -> None:
    bot.add_cog(Ping(bot))
    log.info(f'Extension has been created: {name}')

def teardown(bot: commands.Bot) -> None:
    log.info(f'Extension has been destroyed: {name}')

class PingSetup(discord.ui.View):
    def __init__(self, user: discord.User, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.user = user

    @discord.ui.button(label='Link Steam', style=discord.ButtonStyle.blurple, emoji='🎮')
    async def link(self, button, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(LinkSteam(self.user))

    @discord.ui.button(label='Subscribe', style=discord.ButtonStyle.grey, emoji='📬')
    async def subscribe(self, button, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(Subscribe(self.user))

    @discord.ui.button(label='Unsubscribe', style=discord.ButtonStyle.grey, emoji='📭')
    async def unsubscribe(self, button, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(Unsubscribe(self.user))

class LinkSteam(discord.ui.Modal):
    def __init__(self, user: discord.User, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.add_item(discord.ui.InputText(label='SteamID'))
        self.user = user

    async def callback(self, interaction: discord.Interaction) -> None:
    
        # Validate Steam ID
        steam = SteamID(self.children[0].value)
        if not steam.is_valid():
            log.warn(f"Failed to validate Steam ID `{steam.id}` for user `{self.user.name}` ({self.user.id}). Aborting...")
            await interaction.response.send_message("Failed to validate Steam ID")
            return

        # Find user entity
        with db_session:
            entity = User.get(discord_id=self.user.id)
            if not entity:
                log.warn(f'User `{self.user.name}` ({self.user.id}) not in database. Aborting...')
                await interaction.response.send_message('You are not in the database! Please contact an admin.')
                return

            # Update user entity
            entity.steam_id = steam.as_64
            log.info(f"Succesfully linked Steam account `{steam.as_64}` to user `{self.user.name}` ({self.user.id})")
            await interaction.response.send_message("Succesfully linked Steam account!")

class Subscribe(discord.ui.Modal):
    def __init__(self, discord_user: discord.User, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.add_item(discord.ui.InputText(label='Search pings'))
        self.discord_user = discord_user

    async def callback(self, interaction: discord.Interaction) -> None:
        query = self.children[0].value
        # result = search_pings(query) # TODO implement this
        result = [Ping.get(name=query)]

        # No results found
        if len(result) == 0:
            await interaction.delete_original_response()
            interaction.edit_original_message("I could not find any ping with that name... You could create a new one with this name, or try to search again.", view=PingNotFound(self.discord_user, query))
            log.debug('No ping search results')
            return

        # Conclusive result found
        if len(result) == 1:
            ping = result[0]
            
            with db_session:

                # Fetch database user
                db_user = User.get(discord_id=self.discord_user.id)
                if not db_user:
                    await interaction.delete_original_response()
                    interaction.edit_original_message('You are not in the database! Please contact an admin.')
                    log.error(f'User `{self.discord_user.name}` ({self.discord_user.id}) not in database')
                    return

                # Remove ping from blacklisted pings
                if ping.id in db_user.blacklisted_pings:
                    db_user.blacklisted_pings.remove(ping.id)
                    log.debug(f'Ping `{ping.name}` ({ping.id}) removed from user `{self.discord_user.name}` ({self.discord_user.id}) blacklist')

                # If user has linked their Steam account, and the ping is from steam, fetch steam user
                if db_user.steam_id and ping.steam_id:
                    steam_user = steam_client.getUser(id64=db_user.steam_id)
                    if not steam_user:
                        await interaction.response.send_message(f'Failed to find Steam user `{db_user.steam_id}`. Try relinking your Steam account, or contact an admin.')
                        interaction.edit_original_message(view=PingSetup(self.discord_user)) # TODO add message
                        log.warn(f'Failed to find Steam user `{db_user.steam_id}`')
                        return
                    
                    # If user has the game in their library, they're already subscribed
                    if ping.steam_id in [app.appid for app in steam_user.apps]:
                        await interaction.response.send_message(f'You were already subscribed to this ping, as this game is in your linked Steam library.')
                        interaction.edit_original_message(view=PingSetup(self.discord_user)) # TODO add message
                        log.info(f'User `{self.discord_user.name}` ({self.discord_user.id}) already subscribed to ping `{ping.name}` ({ping.id})')
                        return
                    
                # Check if ping already in whitelist
                if ping.id in db_user.whitelisted_pings:
                    await interaction.response.send_message(f'You were already subscribed to this ping.')
                    interaction.edit_original_message(view=PingSetup(self.discord_user)) # TODO add message
                    log.info(f'User `{self.discord_user.name}` ({self.discord_user.id}) already subscribed to ping `{ping.name}` ({ping.id})')
                    return

                # Add ping to whitelist
                db_user.whitelisted_pings.append(ping.id)
                await interaction.response.send_message()
                interaction.edit_original_message(view=PingSetup(self.discord_user)) # TODO add message
                log.info(f'User `{self.discord_user.name}` ({self.discord_user.id}) subscribed to ping `{ping.name}` ({ping.id})')
                return

class PingNotFound(discord.ui.View):
    def __init__(self, discord_user: discord.User, ping_name: str, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.discord_user = discord_user
        self.ping_name = ping_name

    @discord.ui.button(label='Try again', style=discord.ButtonStyle.blurple)
    async def again(self, button, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(Subscribe(self.discord_user))

    @discord.ui.button(label='Create New Ping', style=discord.ButtonStyle.green)
    async def new(self, button, interaction: discord.Interaction) -> None:
        pass # TODO implement this

    @discord.ui.button(label='Nevermind', style=discord.ButtonStyle.grey)
    async def cancel(self, button, interaction: discord.Interaction) -> None:
        await interaction.edit_original_message(view=PingSetup(self.discord_user)) # TODO add message

class Ping(commands.Cog, name = name, description = 'Better ping utility'):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.group(name='ping', description='Better ping utility', invoke_without_command=True)
    @util.default_command()
    async def ping(self, ctx: commands.Context, flags: list[str], params: list[str]) -> None:
        await ctx.send('No subcommand invoked! Use `$help ping` for usage.') # TODO maybe not lie here
    
    @ping.command(name='setup', description='Ping setup')
    @util.default_command()
    async def setup(self, ctx: commands.Context, flags: list[str], params: list[str]) -> None:
        await ctx.send(view=PingSetup(ctx.author)) # TODO add message and send to dms
