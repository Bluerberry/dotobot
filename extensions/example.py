
import logging
from os.path import basename

from discord.ext import commands
import pony.orm as pony

import lib.entities as entities

# ---------------------> Logging setup


name = basename(__file__)[:-3]
log = logging.getLogger(name)


# ---------------------> Example cog


def setup(bot: commands.Bot) -> None:
    with pony.db_session:
        if entities.Extension.exists(name=name):
            extension = entities.Extension.get(name=name)
            extension.active = True
        else:
            entities.Extension(name=name, active=True)

    bot.add_cog(Example(bot))
    log.info(f'Extension has been created: {name}')

def teardown(bot: commands.Bot) -> None:
    with pony.db_session:
        extension = entities.Extension.get(name=name)
        extension.active = False
    
    log.info(f'Extension has been destroyed: {name}')

class Example(commands.Cog, name = name, description = 'An example extension'):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

