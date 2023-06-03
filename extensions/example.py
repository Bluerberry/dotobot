
import logging
from os.path import basename

from discord.ext import commands

# ---------------------> Logging setup

name = basename(__file__)[:-3]
log = logging.getLogger(name)

# ---------------------> Example cog

def setup(bot: commands.Bot) -> None:
    bot.add_cog(Example(bot))
    log.info(f'Extension has been created: {name}')


def teardown(bot: commands.Bot) -> None:
    log.info(f'Extension has been destroyed: {name}')


class Example(commands.Cog, name = name, description = 'An example extension'):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

