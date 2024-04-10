
from __future__ import annotations

from abc import ABC
import asyncio
import logging
import re as regex
from os.path import basename
from typing import Any

import discord
import pony.orm as pony
from discord.ext import commands

from lib import entities, utility

MAX_VOTE_OPTIONS = 5
MAX_VOTES = 15
DEFAULT_TIMEOUT = 20


# ---------------------> Logging setup


name = basename(__file__)[:-3]
log = logging.getLogger(name)


# ---------------------> UI classes


class VoteButton(discord.ui.Button):
	def __init__(self, parent: Vote | MultiVote, *args, **kwargs) -> None:
		super().__init__(*args, **kwargs)
		self.parent = parent

	async def callback(self, interaction: discord.Interaction) -> None:

		# Check if user has already voted
		if interaction.user in self.parent.votes[interaction.custom_id]:
			await interaction.response.send_message('You have already voted for this option!', ephemeral=True)
			log.debug(f'{interaction.user} has already voted for this option')
			return

		await interaction.response.defer()

		# Update votes
		for option, voters in self.parent.votes.items():
			if interaction.user in voters and option != interaction.custom_id:
				voters.remove(interaction.user)
			elif interaction.user not in voters and option == interaction.custom_id:
				voters.append(interaction.user)

		log.debug(f'{interaction.user} has voted for {interaction.custom_id}')

		# Check if vote has reached threshold
		if any(len(voters) >= self.parent.threshold for voters in self.parent.votes.values()):
			self.parent.resolved = True
			log.info('Vote has reached threshold.')
			return

		# Update parent
		self.parent.timer = self.parent.timeout
		await self.parent.show()

class VoteView(discord.ui.View):
	def __init__(self, parent: Vote | MultiVote, *args, **kwargs) -> None:
		super().__init__(*args, **kwargs)
		for option in parent.votes.keys():
			self.add_item(VoteButton(parent, label=option, custom_id=option, style=discord.ButtonStyle.grey))

class MultiVote:
	def __init__(self, ctx: commands.Context, dialog: utility.Dialog, summary: utility.Summary, prompt: str, options: list[str], anonymous: bool, timeout: int, threshold: int) -> None:
		self.dialog = dialog
		self.summary = summary

		self.timer = timeout
		self.timeout = timeout
		self.anonymous = anonymous
		self.threshold = threshold
		self.votes = {option.capitalize(): [] for option in options}

		self.resolved = False

		self.embed = utility.DefaultEmbed(ctx.bot, prompt, f'Democracy is beautiful. Vote for an option below! This vote **{"will" if anonymous else "wont"}** be anonymous.')
		self.embed.add_field(name='Voting', value='')
		self.view = VoteView(self)

	async def await_resolution(self) -> str:
		await self.show()
		
		# Wait for vote to resolve
		while not self.resolved:
			await asyncio.sleep(1)
			self.timer -= 1
			if self.timer <= 0:
				log.info('Vote has timed out')
				break

		# Find result
		result = max(self.votes, key=lambda option: len(self.votes[option]))

		# Make summary
		self.summary.set_header(f'The people have spoken! `{result}` has won the vote.')
		longest_option = max(len(option) for option in self.votes.keys())

		if self.anonymous:
			factory = utility.ANSIFactory()
			for option, voters in self.votes.items():
				factory.add(option.ljust(longest_option), stroke='bold', colour='green' if option == result else 'white')
				factory.add_raw(f'  {len(voters)}\n')	
			self.summary.set_field('Votes', str(factory))

		else:
			for option, voters in self.votes.items():
				self.summary.set_field(option, '\n'.join(voter.display_name for voter in voters) or 'No one voted for this option')

		return result

	async def show(self) -> None:
		
		# Update UI
		longest_vote = max(len(str(len(voters))) for voters in self.votes.values())
		longest_option = max(len(option) for option in self.votes.keys())
		factory = utility.ANSIFactory()

		for option, voters in self.votes.items():
			vote_count = len(voters)

			# Add vote option to UI
			factory.add(option.ljust(longest_option), stroke='bold')
			factory.add_raw(f'  {str(vote_count).rjust(longest_vote)} ')

			# Add vote bar to UI
			factory.add('█' * vote_count, colour='white')
			factory.add('-' * (self.threshold - vote_count), colour='grey', stroke='bold')
			factory.newline()

		# Update message
		self.embed.set_field_at(0, name='Voting', value=str(factory))
		await self.dialog.set(embed=self.embed, view=self.view)

class Vote:
	def __init__(self, ctx: commands.Context, dialog: utility.Dialog, summary: utility.Summary, prompt: str, anonymous: bool, timeout: int, threshold: int, passing_ratio: int, required_votes: int) -> None:
		self.dialog = dialog
		self.summary = summary

		self.timer = timeout
		self.timeout = timeout
		self.anonymous = anonymous
		self.threshold = threshold
		self.passing_ratio = passing_ratio
		self.required_votes = required_votes
		self.votes = {'yes': [], 'no': []}

		self.resolved = False

		self.embed = utility.DefaultEmbed(ctx.bot, prompt, f'Democracy is beautiful. Vote for an option below! This vote **{"will" if anonymous else "wont"}** be anonymous.')
		self.embed.add_field(name='Voting', value='')
		self.view = VoteView(self)

	async def await_resolution(self) -> str:
		await self.show()

		# Wait for vote to resolve
		while not self.resolved:
			await asyncio.sleep(1)
			self.timer -= 1
			if self.timer <= 0:
				log.info('Vote has timed out.')
				break
		
		# Find result
		yes_votes = len(self.votes['yes'])
		no_votes = len(self.votes['no'])
		total_votes = yes_votes + no_votes
		yes_ratio = round(100 * yes_votes / total_votes) if total_votes else 0
		no_ratio = round(100 * no_votes / total_votes) if total_votes else 0
		result = total_votes >= self.required_votes and yes_ratio >= self.passing_ratio

		# Make summary
		self.summary.set_header(f'The people have voted **{"in favour" if result else "against"}** due to {"a lack of votes" if total_votes < self.required_votes else "a majority vote"}!')

		if self.anonymous:
			factory = utility.ANSIFactory()
			factory.add('In favour'.ljust(11), colour='green', stroke='bold')
			factory.add_raw(f'{yes_ratio}%')
			factory.newline()
			factory.add('Against'.ljust(11), colour='red', stroke='bold')
			factory.add_raw(f'{no_ratio}%')

			self.summary.set_field('Votes', str(factory))

		else:
			self.summary.set_field('In favour', '\n'.join(voter.display_name for voter in self.votes['yes']) or 'No one voted for this option')
			self.summary.set_field('Against', '\n'.join(voter.display_name for voter in self.votes['no']) or 'No one voted for this option')

		return result

	async def show(self) -> None:

		# Update UI
		yes_votes = len(self.votes['yes'])
		no_votes = len(self.votes['no'])
		total_votes = yes_votes + no_votes
		yes_ratio = round(100 * yes_votes / total_votes) if total_votes else 0
		no_ratio = round(100 * no_votes / total_votes) if total_votes else 0
		factory = utility.ANSIFactory()

		# Add vote options to UI
		factory.add_raw(f'{yes_ratio}%')
		factory.add('Yes'.rjust(MAX_VOTES - len(str(yes_ratio)) - 1), stroke='bold')
		factory.add_raw(' │ ')
		factory.add('No'.ljust(MAX_VOTES - len(str(no_ratio)) - 1), stroke='bold')
		factory.add_raw(f'{no_ratio}%')
		factory.newline()

		# Add vote bars to UI
		factory.add('-' * (MAX_VOTES - yes_votes), colour='green', stroke='bold')
		factory.add('█' * yes_votes, colour='green')
		factory.add_raw(' │ ')
		factory.add('█' * no_votes, colour='red')
		factory.add('-' * (MAX_VOTES - no_votes), colour='red', stroke='bold')

		self.embed.set_field_at(0, name='Voting', value=str(factory))
		await self.dialog.set(embed=self.embed, view=self.view)


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
	@utility.signature_command(usage='(str-array) options <(str) --prompt="prompt"> [(int) --threshold="votes"] [(int) --timeout="seconds"] [--anonymous] [--quiet | --verbose]', thesaurus={'prompt': ['p'], 'threshold': ['t'], 'anonymous': ['a']})
	async def vote(self, ctx: commands.Context, dialog: utility.Dialog, summary: utility.Summary, params: dict[str, Any], flags: list[str], vars: dict[str, Any]) -> None:
		multivote = MultiVote(
			ctx, dialog, summary,
			vars['prompt'],
			params['options'][:MAX_VOTE_OPTIONS],
			'anonymous' in flags,
			vars['timeout'] if 'timeout' in vars else DEFAULT_TIMEOUT,
			vars['threshold'] if 'threshold' in vars else MAX_VOTES
		)

		await multivote.await_resolution()

	@commands.command(name='lynch', description='Vote to lynch a user.')
	@utility.signature_command(usage='(str) user [(int) --threshold="votes"] [(int) --timeout="seconds"]  [--quiet | --verbose]')
	async def lynch(self, ctx: commands.Context, dialog: utility.Dialog, summary: utility.Summary, params: dict[str, Any], flags: list[str], vars: dict[str, Any]) -> None:
		user_id = int(regex.match(r'<@(\d+)>', params['user']).group(1))
		user = ctx.guild.get_member(user_id)
		vote = Vote(
			ctx, dialog, summary,
			f'Vote to lynch {user.display_name}',
			'anonymous' in flags,
			vars['timeout'] if 'timeout' in vars else DEFAULT_TIMEOUT,
			vars['threshold'] if 'threshold' in vars else MAX_VOTES,
			3, 60
		)
		
		await vote.await_resolution()