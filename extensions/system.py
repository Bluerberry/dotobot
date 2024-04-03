
# Native libraries
import logging, os, random
from os.path import basename
from typing import Any

# External libraries
import discord, dotenv
from discord.ext import commands
import pony.orm as pony

# Local libraries
from lib import entities, utility


# ---------------------> Setup


# Logging
name = basename(__file__)[:-3]
log = logging.getLogger(name)

# Environment variables
dotenv.load_dotenv()


# ---------------------> System cog


def setup(bot: commands.Bot) -> None:
	with pony.db_session:
		if entities.Extension.exists(name=name):
			extension = entities.Extension.get(name=name)
			extension.active = True

		else:
			entities.Extension(name=name, active=True)

	bot.add_cog(System(bot))
	log.info(f'Extension has been created: {name}')

def teardown(bot: commands.Bot) -> None:
	with pony.db_session:
		extension = entities.Extension.get(name=name)
		extension.active = False

	log.info(f'Extension has been destroyed: {name}')

class System(commands.Cog, name=name, description='Controls internal functionality'):
	def __init__(self, bot: commands.Bot) -> None:
		self.bot = bot

	async def random_status(self) -> None:
		await self.bot.wait_until_ready()
		await self.bot.change_presence(activity=random.choice([
			discord.Activity(type=discord.ActivityType.watching, name='paint dry'),
			discord.Activity(type=discord.ActivityType.watching, name='grass grow'),
			discord.Activity(type=discord.ActivityType.watching, name='yall'),
			discord.Activity(type=discord.ActivityType.playing, name='with myself'),
			discord.Activity(type=discord.ActivityType.playing, name='with your feelings'),
			discord.Activity(type=discord.ActivityType.playing, name='with matches'),
			discord.Activity(type=discord.ActivityType.listening, name='the voices'),
			discord.Activity(type=discord.ActivityType.listening, name='belly sounds'),
			discord.Activity(type=discord.ActivityType.listening, name='static'),
			discord.Activity(type=discord.ActivityType.competing, name='in the paralympics'),
		]))


	# ---------------------> Events


	@commands.Cog.listener()
	async def on_ready(self) -> None:

		# Add all members from all guilds to database
		with pony.db_session:
			for guild in self.bot.guilds:
				for member in guild.members:
					if self.bot.application_id == member.id:
						continue

					if entities.User.exists(discord_id=member.id):
						log.debug(f'User `{member.name}` ({member.id}) already known')
						continue

					entities.User(discord_id=member.id)
					log.info(f'User `{member.name}` ({member.id}) added to the database')

		# Set random status
		await self.random_status()
		log.debug('Random status set')
		log.info(f'Succesful login as {self.bot.user}')

	@commands.Cog.listener()
	async def on_member_join(self, member: discord.User) -> None:

		# Check if new user is already known
		with pony.db_session:
			if entities.User.exists(discord_id=member.id):
				log.debug(f'New member `{member.name}` ({member.id}) already known')
				return

			entities.User(discord_id=member.id)
			log.info(f'New member `{member.name}` ({member.id}) added to the database')

		# Find greet channel
		channel = self.bot.get_channel(int(os.getenv('GREET_CHANNEL_ID')))
		if channel == None:
			log.error(f'Failed to load greet channel ({os.getenv("GREET_CHANNEL_ID")})')
			return

		# Send greetings
		await channel.send(f'Welcome {member.mention}, to {channel.guild.name}!')

	@commands.Cog.listener()
	async def on_command(self, ctx: commands.Context) -> None:
		log.info(f'Command `{ctx.command}` invoked by `{ctx.author.name}` ({ctx.author.id}) in `{ctx.guild}` ({ctx.guild.id})')

	@commands.Cog.listener()
	async def on_command_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
		if isinstance(error, commands.errors.CommandNotFound):
			return

		log.error(error)


	# ---------------------> Commands


	@commands.command(name='summary', description='Provides summary of previous command, or reference command.')
	@utility.signature_command()
	async def summary(self, ctx: commands.Context, dialog: utility.Dialog, summary: utility.Summary, params: dict[str, Any], flags: list[str], vars: dict[str, Any]) -> None:

		# Finding summary to provide
		reference = ctx.message.reference
		if reference == None:
			target_summary = utility.history.last()
			log.debug(f'Following last-command branch for {ctx.prefix}{ctx.command}')

		else:
			target_summary = utility.history.search(reference.message_id)
			log.debug(f'Following reference branch for {ctx.prefix}{ctx.command}')

		# Check if summary exists
		if target_summary == None:
			summary.set_header('No summary found')
			log.warn('Failed to provide summary')
			return

		# Provide summary
		summary.send_on_return = False
		await dialog.add(embed=target_summary.make_embed())

	@commands.command(name='load', description='Loads extensions by name.')
	@utility.signature_command(usage='<(str-array) extensions | --all> [--quiet | --verbose]', thesaurus={'all': ['a']})
	@utility.dev_only()
	async def load(self, ctx: commands.Context, dialog: utility.Dialog, summary: utility.Summary, params: dict[str, Any], flags: list[str], vars: dict[str, Any]) -> None:

		# Prepare extension paths
		if 'all' in flags:
			extensions = list(utility.yield_extensions(prefix_path=True))
			log.debug(f'Following --all branch for {ctx.prefix}{ctx.command}')

		else:
			extensions = [utility.extension_path(extension) for extension in params['extensions']]
			log.debug(f'Following parameter branch for {ctx.prefix}{ctx.command}')

		if not extensions:
			summary.set_header('No extensions found')
			log.error('No extensions or flags provided')
			return

		# Load extensions
		field = ''
		success = 0
		for extension in extensions:
			try:
				self.bot.load_extension(extension)
				field += f'🟢 {utility.extension_name(extension).capitalize()} sucessfully loaded\n'
				success += 1

			except discord.ExtensionAlreadyLoaded as err:
				log.warning(err)
				field += f'🟡 {utility.extension_name(extension).capitalize()} was already loaded\n'

			except discord.ExtensionNotFound as err:
				log.warning(err)
				field += f'🟠 {utility.extension_name(extension).capitalize()} doesn\'t exist\n'

			except Exception as err:
				log.error(err)
				field += f'🔴 {utility.extension_name(extension).capitalize()} failed to load\n'

		# Build summary
		if success == 0:
			summary.set_header('No extension have loaded')
			summary.set_field('Extensions', field)

		elif success == len(extensions):
			summary.set_header('All extensions have loaded')
			summary.set_field('Extensions', field)

		else:
			summary.set_header(f'{success} out of {len(extensions)} extensions have loaded')
			summary.set_field('Extensions', field)

	@commands.command(name='unload', description='Unloads extensions by name.')
	@utility.signature_command(usage='<(str-array) extensions | --all> [--quiet | --verbose]', thesaurus={'all': ['a']})
	@utility.dev_only()
	async def unload(self, ctx: commands.Context, dialog: utility.Dialog, summary: utility.Summary, params: dict[str, Any], flags: list[str], vars: dict[str, Any]) -> None:

		# Prepare extension paths
		if 'all' in flags:
			extensions = list(self.bot.extensions.keys())
			log.debug(f'Following --all branch for {ctx.prefix}{ctx.command}')

		else:
			extensions = [utility.extension_path(extension) for extension in params['extensions']]
			log.debug(f'Following parameter branch for {ctx.prefix}{ctx.command}')

		if not extensions:
			summary.set_header('No extensions or flags provided')
			log.error('No extensions or flags provided')
			return

		# Unload extensions
		field = ''
		success = 0
		for extension in extensions:
			if utility.extension_name(extension) == 'system':
				field += f'🔴 {utility.extension_name(extension).capitalize()} shouldn\'t unload\n'
				continue

			try:
				self.bot.unload_extension(extension)
				field += f'🟢 {utility.extension_name(extension).capitalize()} sucessfully unloaded\n'
				success += 1

			except discord.ExtensionNotLoaded as err:
				log.warning(err)
				field += f'🟡 {utility.extension_name(extension).capitalize()} was already unloaded\n'

			except discord.ExtensionNotFound as err:
				log.warning(err)
				field += f'🟠 {utility.extension_name(extension).capitalize()} doesn\'t exist\n'

			except Exception as err:
				log.error(err)
				field += f'🔴 {utility.extension_name(extension).capitalize()} failed to unload\n'

		# Build summary
		if not success:
			summary.set_header('No extension have unloaded')
			summary.set_field('Extensions', field)

		elif len(extensions) == success:
			summary.set_header('All extensions have unloaded')
			summary.set_field('Extensions', field)

		else:
			summary.set_header(f'{success} out of {len(extensions)} extensions have unloaded')
			summary.set_field('Extensions', field)

	@commands.command(name='reload', description='Reloads extensions by name.')
	@utility.signature_command(usage='<(str-array) extensions | --all> [--quiet | --verbose]', thesaurus={'all': ['a']})
	@utility.dev_only()
	async def reload(self, ctx: commands.Context, dialog: utility.Dialog, summary: utility.Summary, params: dict[str, Any], flags: list[str], vars: dict[str, Any]) -> None:

		# Prepare extension paths
		if 'all' in flags:
			extensions = list(self.bot.extensions.keys())
			log.debug(f'Following --all branch for {ctx.prefix}{ctx.command}')

		else:
			extensions = [utility.extension_path(extension) for extension in params['extensions']]
			log.debug(f'Following parameter branch for {ctx.prefix}{ctx.command}')

		if not extensions:
			summary.set_header('No extensions or flags provided')
			log.error('No extensions or flags provided')
			return

		# Reload extensions
		field = ''
		success = 0
		for extension in extensions:
			try:
				self.bot.reload_extension(extension)
				field += f'🟢 {utility.extension_name(extension).capitalize()} sucessfully reloaded\n'
				success += 1

			except discord.ExtensionNotLoaded as err:
				log.warning(err)
				field += f'🟡 {utility.extension_name(extension).capitalize()} wasn\'t loaded\n'

			except discord.ExtensionNotFound as err:
				log.warning(err)
				field += f'🟠 {utility.extension_name(extension).capitalize()} doesn\'t exist\n'

			except Exception as err:
				log.error(err)
				field += f'🔴 {utility.extension_name(extension).capitalize()} failed to reload\n'

		# Build summary
		if not success:
			summary.set_header('No extension have reloaded')
			summary.set_field('Extensions', field)

		elif len(extensions) == success:
			summary.set_header('All extensions have reloaded')
			summary.set_field('Extensions', field)

		else:
			summary.set_header(f'{success} out of {len(extensions)} extensions have reloaded')
			summary.set_field('Extensions', field)

	@commands.command(name='status', description='Displays extension statuses by name.')
	@utility.signature_command(usage='<(str-array) extensions | --all> [--quiet | --verbose]', thesaurus={'all': ['a']})
	async def status(self, ctx: commands.Context, dialog: utility.Dialog, summary: utility.Summary, params: dict[str, Any], flags: list[str], vars: dict[str, Any]) -> None:
		print('entered command')
		known  = list(utility.yield_extensions(prefix_path=True))
		loaded = list(self.bot.extensions.keys())

		# Prepare extension paths
		if 'all' in flags:
			extensions = known
			log.debug(f'Following --all branch for {ctx.prefix}{ctx.command}')

		else:
			extensions = [utility.extension_path(extension) for extension in params['extensions']]
			log.debug(f'Following parameter branch for {ctx.prefix}{ctx.command}')

		if not extensions:
			summary.set_header('No extensions found')
			log.error('No extensions found')
			return

		# Check status
		field = ''
		active, inactive = 0, 0
		for extension in extensions:
			if extension not in known:
				field += f'🟠 {utility.extension_name(extension).capitalize()} doesn\'t exist\n'

			elif extension in loaded:
				field += f'🟢 {utility.extension_name(extension).capitalize()} is activated\n'
				active += 1

			else:
				field += f'🔴 {utility.extension_name(extension).capitalize()} is deactivated\n'
				inactive += 1

		# Feedback
		if not active:
			summary.set_header('No extensions are active')
			summary.set_field('Extensions', field)

		elif not inactive:
			summary.set_header('All extensions are active')
			summary.set_field('Extensions', field)

		else:
			summary.set_header(f'{active} out of {active + inactive} extensions are active')
			summary.set_field('Extensions', field)

	@commands.command(name='dump', description='Dumps bot log')
	@utility.signature_command(usage='[--quiet | --verbose]')
	@utility.dev_only()
	async def dump(self, ctx: commands.Context, dialog: utility.Dialog, summary: utility.Summary, params: dict[str, Any], flags: list[str], vars: dict[str, Any]) -> None:
		try:
			with open('logs//main.log', 'br') as file:
				await ctx.reply(file=discord.File(file, 'main.log'))

		except Exception as err:
			summary.set_header('Failed to dump log')
			log.error(err)

	@commands.command(name='activity', description='Sets bot activity')
	@utility.signature_command(usage='<--random | --playing="activity" | --watching="activity" | --listening="activity" | --competing="activity"> [--verbose | --quiet]', thesaurus={'random': ['r'], 'playing': ['p'], 'watching': ['w'], 'listening': ['l'], 'competing': ['c']})
	@utility.dev_only()
	async def activity(self, ctx: commands.Context, dialog: utility.Dialog, summary: utility.Summary, params: dict[str, Any], flags: list[str], vars: dict[str, Any]) -> None:

		# Check if random activity is requested
		if 'random' in flags:
			log.debug(f'Following random branch for {ctx.prefix}{ctx.command}')
			await self.random_status()
			summary.set_header('Random activity selected')
			log.info('Random activity selected')
			return

		# Set activity
		if 'competing' in vars:
			activity_type = discord.ActivityType.competing
			name = vars['competing']
		elif 'watching' in vars:
			activity_type = discord.ActivityType.watching
			name = vars['watching']
		elif 'listening' in vars:
			activity_type = discord.ActivityType.listening
			name = vars['listening']
		elif 'playing' in vars:
			activity_type = discord.ActivityType.playing
			name = vars['playing']

		await self.bot.change_presence(activity=discord.Activity(type=activity_type, name=name))

		summary.set_header('New activity set')
		summary.set_field('New activity', f'`{name}`')
		log.info(f'Activity set to `{name}`')
