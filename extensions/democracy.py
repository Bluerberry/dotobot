
from __future__ import annotations

import asyncio
import logging
from os.path import basename
from typing import Any

import discord
import pony.orm as pony
from discord.ext import commands

from lib import entities, utility

MAX_VOTE_OPTIONS = 5
MAX_VOTE_WIDTH = 15


# ---------------------> Logging setup


name = basename(__file__)[:-3]
log = logging.getLogger(name)


# ---------------------> UI classes


class VoteButton(discord.ui.Button):
	def __init__(self, parent: VoteUI, *args, **kwargs) -> None:
		super().__init__(*args, **kwargs)
		self.parent = parent

	async def callback(self, interaction: discord.Interaction) -> None:

		# Check if user has already voted
		if interaction.user in self.parent.votes[interaction.custom_id]:
			await interaction.response.send_message('You have already voted for this option!', ephemeral=True)
			return

		await interaction.response.defer()

		# Update votes
		for option, voters in self.parent.votes.items():
			if interaction.user in voters and option != interaction.custom_id:
				voters.remove(interaction.user)
			elif interaction.user not in voters and option == interaction.custom_id:
				voters.append(interaction.user)

		self.parent.result = max(self.parent.votes, key=lambda option: len(self.parent.votes[option]))

		# Update UI
		if self.parent.threshold is not None and any(len(voters) >= self.parent.threshold for voters in self.parent.votes.values()):
			self.parent.resolved.set()
		self.parent.update_votes()

class VoteView(discord.ui.View):
	def __init__(self, parent: VoteUI) -> None:
		super().__init__()

		# Add buttons
		for option in parent.votes.keys():
			self.add_item(VoteButton(parent, label=option, custom_id=option, style=discord.ButtonStyle.grey))

class VoteEmbed(utility.DefaultEmbed):
	def __init__(self, ctx: commands.Context, prompt: str, options: list[str], anonymous: bool, threshold: int | None = None, timeout: int | None = None) -> None:
		super().__init__(ctx.bot, prompt, f'Democracy is beautiful. Vote for an option below! This vote **{"will" if anonymous else "wont"}** be anonymous.')

		# Parameters
		self.votes = {option: [] for option in options}
		self.anonymous = anonymous
		self.threshold = threshold
		self.timeout = timeout

		# Resolution
		self.resolved = asyncio.Event()
		self.result = None

		# Create UI
		self.ctx = ctx
		self.view = VoteButtons(self)
		self.update_votes()



	async def await_resolution(self) -> str:
		try:
			async with asyncio.timeout(self.timeout):
				await self.resolved.wait()
		except asyncio.TimeoutError:
			log.info('Vote has timed out.')
		else:
			log.info('Vote has been resolved.')

		self.view.clear_items()
		self.update_votes()
		return self.result

	def update_votes(self) -> None:
		longest_vote = max(len(str(len(voters))) for voters in self.votes.values())
		longest_option = max(len(option) for option in self.votes.keys())
		factory = utility.ANSIFactory()

		for option, voters in self.votes.items():
			vote_count = len(voters)

			# Add vote option to UI
			if self.threshold is not None and any(len(voters) >= self.threshold for voters in self.votes.values()):
				factory.add_raw('✅ ' if vote_count >= self.threshold else '⛔ ')
			factory.add(f'{option.ljust(longest_option)} │ {str(vote_count).rjust(longest_vote)} ')

			# Add vote bar to UI
			if self.threshold is not None:
				factory.add('█' * min(vote_count, self.threshold - 1), colour='white')
				if vote_count > self.threshold - 1:
					factory.add('█' * (vote_count - self.threshold + 1), colour='green')
					factory.add('-' * (MAX_VOTE_WIDTH - vote_count), colour='green', stroke='bold')

				else:
					factory.add('-' * (self.threshold - vote_count - 1), colour='grey', stroke='bold')
					factory.add('-' * (MAX_VOTE_WIDTH - self.threshold + 1), colour='green', stroke='bold')
			else:
				factory.add('█' * vote_count, colour='white')
				factory.add('-' * (MAX_VOTE_WIDTH - vote_count), colour='grey', stroke='bold')

			factory.add_raw('\n')

		self.add_field(name='Options', value=str(factory))


# ---------------------> Democracy cog


def setup(bot: commands.Bot) -> None:
	with pony.db_session:
		if entities.Extension.exists(name=name):
			extension = entities.Extension.get(name=name)
			extension.active = True

		else:
			entities.Extension(name=name, active=True)

	bot.add_cog(Democracy(bot))
	log.info(f'Extension has been created: {name}')

def teardown(bot: commands.Bot) -> None:
	with pony.db_session:
		extension = entities.Extension.get(name=name)
		extension.active = False

	log.info(f'Extension has been destroyed: {name}')

class Democracy(commands.Cog, name = name, description = 'Voting, lynching, etc.'):
	def __init__(self, bot: commands.Bot) -> None:
		self.bot = bot

	@commands.command(name='vote', description='Vote for an option.')
	@utility.signature_command(usage='(str-array) options <(str) --prompt="prompt"> <(int) --threshold="votes" / (int) --timeout="seconds"> [--anonymous] [--quiet | --verbose]')
	async def vote(self, ctx: commands.Context, dialog: utility.Dialog, summary: utility.Summary, params: dict[str, Any], flags: list[str], vars: dict[str, Any]) -> utility.Summary:

		# Setup vote
		voteUI = VoteUI(
			self.bot,
			vars['prompt'],
			params['options'],
			'anonymous' in flags,
			vars['threshold'] if 'threshold' in vars else None,
			params['timeout'] if 'timeout' in params else None
			)

		# Start voting
		await dialog.set(embed=voteUI, view=voteUI.view)
		await voteUI.await_resolution()

		return summary