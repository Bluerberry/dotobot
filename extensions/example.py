
# NOTE This is an example extension. It is not meant to be used as is. It is meant to be copied and modified to create new extensions.

# Native libraries
import logging
from os.path import basename
from typing import Any

# External libraries
from discord.ext import commands
import pony.orm as pony

# Local libraries
from lib import entities, utility


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

	@commands.command(name='example', aliases=['ex', ' test'], description='An example command')
	@utility.signature_command(usage='<(int) required> [--optional]')
	async def example(self, ctx: commands.Context, dialog: utility.Dialog, summary: utility.Summary, params: dict[str, Any], flags: list[str], vars: dict[str, Any]) -> None:
		await ctx.send(f'{params}\n{flags}\n{vars}')
