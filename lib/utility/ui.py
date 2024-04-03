
# Native libraries
import asyncio

# External libraries
import discord
from discord.ext import commands

# Local libraries
from . import errors


# ---------------------> Menu's


class ContinueAbortMenu(discord.ui.View):
	def __init__(self, *args, authorised_user: discord.User = None, **kwargs) -> None:
		super().__init__(*args, **kwargs)
		self.authorised_user = authorised_user
		self.responded = asyncio.Event()
		self.result = None

	async def await_response(self) -> bool:
		await self.responded.wait()
		return self.result

	@discord.ui.button(label='Continue', style=discord.ButtonStyle.green, emoji='🚶‍♂️')
	async def override(self, _, interaction: discord.Interaction) -> None:
		if self.authorised_user != None and self.authorised_user != interaction.user:
			await interaction.response.send_message('You are not authorised to do that.', ephemeral=True)
			return

		await interaction.response.defer()
		self.disable_all_items()
		self.result = True
		self.responded.set()

	@discord.ui.button(label='Abort', style=discord.ButtonStyle.red, emoji='👶')
	async def abort(self, _, interaction: discord.Interaction) -> None:
		if self.authorised_user != None and self.authorised_user != interaction.user:
			await interaction.response.send_message('You are not authorised to do that.', ephemeral=True)
			return

		await interaction.response.defer()
		self.disable_all_items()
		self.result = False
		self.responded.set()


# ---------------------> External Classes


class DefaultEmbed(discord.Embed):
	def __init__(self, bot: commands.Bot, title: str = '', description: str = '', author: bool = False, footer: bool = True, color: int = 0) -> None:
		palette = [
			discord.Colour.from_rgb(255, 89,  94 ), # Red
			discord.Colour.from_rgb(255, 202, 58 ), # Yellow
			discord.Colour.from_rgb(138, 201, 38 ), # Green
			discord.Colour.from_rgb(25,  130, 196), # Blue
			discord.Colour.from_rgb(106, 76,  147)  # Purple
		]

		super().__init__(
			title=title,
			description=description,
			color=palette[color % 5]
		)

		if author:
			self.set_author(name=bot.user.name)
		if footer:
			self.set_footer(text=f'Powered by {bot.user.name}')

class ANSIFactory:
	def __init__(self) -> None:
		self.text = '```ansi\n[0m'

	def __str__(self) -> str:
		return self.text + '[0m```'

	def add_raw(self, text: str) -> None:
		self.text += text

	def add(self, text: str, colour: str = 'default', stroke: str = 'default') -> None:
		self.text += '[' # Start escape sequence

		# Set stroke
		if stroke == 'default':
			self.text += '0;'
		elif stroke == 'bold':
			self.text += '1;'
		elif stroke == 'underline':
			self.text += '4;'
		else:
			raise errors.UnknownANSIStrokeError()

		# Set colour
		if colour == 'default':
			self.text += '39m'
		elif colour == 'grey':
			self.text += '30m'
		elif colour == 'red':
			self.text += '31m'
		elif colour == 'green':
			self.text += '32m'
		elif colour == 'yellow':
			self.text += '33m'
		elif colour == 'blue':
			self.text += '34m'
		elif colour == 'magenta':
			self.text += '35m'
		elif colour == 'cyan':
			self.text += '36m'
		elif colour == 'white':
			self.text += '37m'
		else:
			raise errors.UnknownANSIColourError()

		# Add text
		self.text += text + '[0m'

class Dialog:
	def __init__(self, ctx: commands.Context) -> None:
		self.ctx = ctx
		self.dialog = None

	async def set(self, *args, **kwargs) -> discord.Message:
		if self.dialog == None:
			self.dialog = await self.ctx.reply(*args, **kwargs)
		else:
			self.dialog = await self.dialog.edit(*args, **kwargs)
		return self.dialog

	async def add(self, *args, **kwargs) -> discord.Message:
		return await self.ctx.reply(*args, **kwargs)

	async def cleanup(self) -> None:
		if self.dialog:
			await self.dialog.delete()

class Summary:
	def __init__(self, ctx: commands.Context, send_on_return: bool = True) -> None:
		self.ctx = ctx
		self.fields = {}
		self.send_on_return = send_on_return

	def make_embed(self) -> discord.Embed | None:
		if not self.header:
			return None

		embed = DefaultEmbed(self.ctx.bot, 'Summary', self.header)
		for name, value in self.fields.items():
			embed.add_field(name=name, value=value)

		return embed

	def set_header(self, header: str) -> None:
		self.header = header

	def set_field(self, name: str, value: str) -> None:
		self.fields[name] = value

class History:
	history = []

	def add(self, summary: Summary) -> None:
		self.history.append(summary)
		self.history = self.history[-10:]

	def last(self) -> Summary | None:
		if len(self.history) == 0:
			return

		return self.history[-1]

	def search(self, id: int) -> Summary | None:
		for summary in self.history:
			if summary.ctx.message.id == id:
				return summary

		return

history = History()