
import logging
from os.path import basename

import discord
from discord.ext import commands
from pony.orm import db_session
from steam.steamid import SteamID

from entities import User

# ---------------------> Logging setup

name = basename(__file__)[:-2]
log = logging.getLogger(name)

# ---------------------> Example cog

def setup(bot: commands.Bot) -> None:
    bot.add_cog(Ping(bot))
    log.info(f'Extension has been created: {name}')

def teardown(bot: commands.Bot) -> None:
    log.info(f'Extension has been destroyed: {name}')

class SteamSetup(discord.ui.Modal):
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
            entity = User.get(user_id=self.user.id)
            if not entity:
                log.warn(f'User `{self.user.name}` ({self.user.id}) not in database. Aborting...')
                await interaction.response.send_message('You are not in the database! Please contact an admin.')
                return
            
            # Update user entity
            entity.steam_id = steam.id
            log.info(f"Succesfully linked Steam account `{steam.id}` to user `{self.user.name}` ({self.user.id})")
            await interaction.response.send_message("Succesfully linked Steam account!")

class Ping(commands.Cog, name = name, description = 'Better ping utility'):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

