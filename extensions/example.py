
import logging
from os.path import basename
from typing import Any

from discord.ext import commands
import pony.orm as pony

import lib.entities as entities
import lib.utility as utility

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

    @commands.command(name='example', description = 'An example command')
    @utility.signature_command(usage='[optional] <--required>')
    async def example(self, ctx: commands.Context, dialog: utility.Dialog, summary: utility.Summary, params: dict[str, Any], flags: list[str], vars: dict[str, Any]) -> None:
        await ctx.send(f'{params}\n{flags}\n{vars}')
