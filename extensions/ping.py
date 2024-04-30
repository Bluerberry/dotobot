
# Native libraries
import asyncio, logging, os, random
from os.path import basename
from typing import Any

# External libraries
import discord, dotenv
import pony.orm as pony
from discord.ext import commands

# Local libraries
from lib import entities, utility, steam


# ---------------------> Setup


# Logging
name = basename(__file__)[:-3]
log = logging.getLogger(name)

# Environment variables
dotenv.load_dotenv()


# ---------------------> UI classes


class SelectPingGroup(discord.ui.Select):
	def __init__(self, parent: discord.ui.View, options: list[entities.PingGroup], *args, **kwargs) -> None:
		super().__init__(
			placeholder='Select a ping group',
			options=[discord.SelectOption(label=option.name, value=str(option.id)) for option in options],
			*args, **kwargs
		)

		self.parent = parent

	async def callback(self, interaction: discord.Interaction) -> None:

		 # Only authorised users can interact
		if interaction.user != self.parent.authorised_user:
			await interaction.response.send_message('You are not authorised to do that.', ephemeral=True)
			return

		await interaction.response.defer()

class VaguePingGroup(discord.ui.View):
	def __init__(self, authorised_user: discord.User, options: list[entities.PingGroup], *args, **kwargs) -> None:
		super().__init__(*args, **kwargs)
		self.authorised_user = authorised_user
		self.resolved = asyncio.Event()
		self.result = None

		# Create select menu
		self.select = SelectPingGroup(self, options)
		self.add_item(self.select)

	async def await_resolution(self) -> entities.PingGroup | None:
		await self.resolved.wait()
		self.disable_all_items()
		return self.result

	@discord.ui.button(label='Abort', style=discord.ButtonStyle.red, emoji='👶', row=1)
	async def abort(self, _, interaction: discord.Interaction) -> None:

		# Only authorised users can interact
		if interaction.user != self.authorised_user:
			await interaction.response.send_message('You are not authorised to do that.', ephemeral=True)
			return

		await interaction.response.defer()
		self.resolved.set()
	
	@discord.ui.button(label='Resolve', style=discord.ButtonStyle.green, emoji='👍', row=1)
	async def resolve(self, _, interaction: discord.Interaction) -> None:
		
		# Only authorised users can interact
		if interaction.user != self.authorised_user:
			await interaction.response.send_message('You are not authorised to do that.', ephemeral=True)
			return

		await interaction.response.defer()
		with pony.db_session:
			self.result = entities.PingGroup.get(id=int(self.select.values[0]))
		self.resolved.set()

# ---------------------> Ping cog


def setup(bot: commands.Bot) -> None:
	with pony.db_session:
		if entities.Extension.exists(name=name):
			extension = entities.Extension.get(name=name)
			extension.active = True

		else:
			entities.Extension(name=name, active=True)

	bot.add_cog(Ping(bot))
	log.info(f'Extension has been created: {name}')

def teardown(bot: commands.Bot) -> None:
	with pony.db_session:
		extension = entities.Extension.get(name=name)
		extension.active = False

	log.info(f'Extension has been destroyed: {name}')

class Ping(commands.Cog, name=name, description='Better ping utility'):
	def __init__(self, bot: commands.Bot) -> None:
		self.bot = bot
		self.steam = steam.Client(os.getenv('STEAM_TOKEN'))

	async def update_pings(self, summary: utility.Summary | None = None) -> None:
		with pony.db_session:

			# Fetch new Steam data and update ping groups
			for db_user in entities.User.select(lambda db_user: db_user.steam_id):
				steam_user = self.steam.getUser(db_user.steam_id)

				# Check if Steam profile is private
				if steam_user.private:
					log.warning(f'User `{ await self.bot.fetch_user(db_user.discord_id).name }` ({db_user.discord_id}) has their Steam library on private')
					continue

				# Update ping groups
				new = 0
				for game in steam_user.games:
					if not entities.PingGroup.exists(steam_id=game.id):
						try:
							game.unlazify()

						except steam.errors.GameNotFoundError:
							log.warning(f'No game with id ({game.id}) could be found in the Steam store')
							continue

						# Create new ping group
						try:
							entities.PingGroup(name=game.name, steam_id=game.id)
							log.info(f'Created ping group `{game.name}` ({game.id})')
							new += 1

						except pony.core.CacheIndexError:
							log.warn(f'Failed to create ping group with duplicate name or SteamID')

				if summary and new:
					summary.set_field('New ping groups', f'Created {new} new ping group(s). For specifics, consult the logs.')

	async def find_pinggroup(self, query: str, dialog: utility.Dialog, summary: utility.Summary) -> entities.PingGroup | None:

		# Search ping groups
		with pony.db_session:
			options = []
			for pg in pony.select(pg for pg in entities.PingGroup):
				options.append(utility.SearchItem(pg, pg.name))
				for alias in pg.aliases:
					options.append(utility.SearchItem(pg, alias))

			conclusive, results = utility.fuzzy_search(options, query)

			if not results:
				log.error('No ping groups were found, search returned nothing')
				summary.set_header('No ping groups found')
				return

			# Results were conclusive
			if conclusive:
				pingGroup = results[0].item
				log.debug(f'Search results were conclusive, found ping group `{pingGroup.name}`')
				return pingGroup

			# Results weren't conclusive, send VaguePingGroup menu
			else:
				log.debug(f'Search results were inconclusive')
				view = VaguePingGroup(dialog.ctx.author, [result.item for result in results[:5]])
				await dialog.set('Search results were inconclusive! Did you mean any of these ping groups?', view=view)
				pingGroup = await view.await_resolution()

				# Parse result
				if not pingGroup:
					log.warning(f'User `{dialog.ctx.author.name}` ({dialog.ctx.author.id}) aborted ping command.')
					summary.set_header('ping command was aborted')
					return

				log.debug(f'User chose `{pingGroup.name} from inconclusive search results')
				return pingGroup


	# ---------------------> Commands


	@commands.group(name='ping', description='Better ping utility', invoke_without_command=True)
	@utility.signature_command(usage='<(long-string) name> [--quiet | --verbose]')
	async def ping(self, ctx: commands.Context, dialog: utility.Dialog, summary: utility.Summary, params: dict[str, Any], flags: list[str], vars: dict[str, Any]) -> None:

		# Update ping groups
		if 'quiet' not in flags:
			await dialog.set('DoSsing the Steam API...')
		await self.update_pings(summary)

		with pony.db_session:

			# Find ping group
			db_pingGroup = await self.find_pinggroup(' '.join(params['name']), dialog, summary)
			if not db_pingGroup:
				return

			# Find explicit subscribers
			subscribers = list(entities.User.select(lambda db_user: db_pingGroup.id in db_user.whitelisted_pings))

			# Find implicit subscribers
			if db_pingGroup.steam_id:
				for db_user in entities.User.select(lambda db_user: db_user.steam_id):
					if db_pingGroup.id not in db_user.blacklisted_pings and db_user.discord_id not in subscribers:
						steam_user = self.steam.getUser(db_user.steam_id)
						if db_pingGroup.steam_id in [game.id for game in steam_user.games]:
							subscribers.append(db_user)

			# Build and send ping message
			discord_users = [await self.bot.fetch_user(subscriber.discord_id) for subscriber in subscribers]
			message = random.choice([
				f'Hear ye, hear ye! Thou art did request to attend the court of {db_pingGroup.name}.\n',
				f'Get in loser, we\'re going to do some {db_pingGroup.name}.\n',
				f'The definition of insanity is launching {db_pingGroup.name} and expecting success. Let\'s go insane.\n',
				f'Whats more important, working on your future or joining {db_pingGroup.name}? Exactly.\n',
				f'The ping extention wasted weeks of my life, so thank you for using it. Lets play {db_pingGroup.name}!\n',
				f'Los gezelligitos, donde esta genietos? Ah! Costa del {db_pingGroup.name}.\n',
				f'Inspiratie is voor de inspiratielozen. Something something {db_pingGroup.name}.\n'
			]) + ' '.join([user.mention for user in discord_users])

			await dialog.add(message, view=None, mention_author=False)

		summary.send_on_return = False
		summary.set_header('Successfully sent out ping')
		summary.set_field('Subscribers', '\n'.join([user.name for user in discord_users]))

	@ping.command(name='setup', description='Ping setup')
	@utility.signature_command(usage='<(int) steamID64> [--force] [--quiet | --verbose]', thesaurus={'force': ['f']})
	async def setup(self, ctx: commands.Context, dialog: utility.Dialog, summary: utility.Summary, params: dict[str, Any], flags: list[str], vars: dict[str, Any]) -> None:

		# Validate SteamID
		try:
			if 'quiet' not in flags:
				await dialog.set('DoSsing the Steam API...')
			steam_user = self.steam.getUser(id64=params['steamID64'])

		except steam.errors.UserNotFoundError:
			summary.set_header('Invalid SteamID')
			summary.set_field('ValueError', f'SteamID `{params["steamID64"]}` could not be found. Make sure you provide your Steam ID64, found in your profile url.')
			log.warn(f'Invalid SteamID: `{params["steamID64"]}`')
			return

		# Link Steam account
		with pony.db_session:
			db_user = entities.User.get(discord_id=ctx.author.id)

			# Check if there already is a SteamID registered to this user
			if db_user.steam_id and 'force' not in flags:
				log.debug(f'User `{ctx.author.name}` ({ctx.author.id}) already has linked Steam account')

				# Prompt with override
				view = utility.ContinueCancelMenu(ctx.author)
				await dialog.set('You already have a linked Steam account. Do you want to override the old account, or keep it?', view=view)
				result = await view.await_response()

				# Cleanup
				if not result:
					log.info(f'User `{ctx.author.name}` ({ctx.author.id}) aborted ping setup')
					summary.set_field('Subscriptions', 'No subscriptions added.')
					summary.set_header('User aborted ping setup')
					return

			# Link Steam account
			db_user.steam_id = steam_user.id64
			if 'quiet' not in flags:
				await dialog.set('DoSsing the Steam API...', view=None)
			await self.update_pings(summary)

		# Update log and summary
		if steam_user.private:
			summary.set_field('New Subscriptions', 'No subscriptions added, Steam profile is set to private. When you set your profile to public you will be automatically subscribed to all games in your library.')
		else:
			summary.set_field('New Subscriptions', 'Steam library added to subscribed ping groups!')

		summary.set_header(f'Sucessfully linked Steam account `{steam_user.name}` to user `{ctx.author.name}`')
		log.info(f'Succesfully linked Steam account `{steam_user.name}` ({steam_user.id64}) to user `{ctx.author.name}` ({ctx.author.id})')

	@ping.command(name='subscribe', description='Subscribe to a ping group')
	@utility.signature_command(usage='<(long-string) name> [--quiet | --verbose]')
	async def subscribe(self, ctx: commands.Context, dialog: utility.Dialog, summary: utility.Summary, params: dict[str, Any], flags: list[str], vars: dict[str, Any]) -> None:

		# Update ping groups
		if 'quiet' not in flags:
			await dialog.set('DoSsing the Steam API...')
		await self.update_pings(summary)

		# Subscribe to ping group
		with pony.db_session:

			# Find ping group
			db_user = entities.User.get(discord_id=ctx.author.id)
			db_pingGroup = await self.find_pinggroup(' '.join(params['name']), dialog, summary)
			if not db_pingGroup:
				return
			
			if db_pingGroup.id in db_user.blacklisted_pings:
				db_user.blacklisted_pings.remove(db_pingGroup.id)

			else:

				# Check if user is manually subscribed
				if db_pingGroup.id in db_user.whitelisted_pings:
					summary.set_field('User already subscribed', f'User `{ctx.author.name}` ({ctx.author.id}) already subscribed to ping group `{db_pingGroup.name}` ({db_pingGroup.id})')
					log.warning(f'User `{ctx.author.name}` ({ctx.author.id}) already subscribed to ping group `{db_pingGroup.name}` ({db_pingGroup.id})')
					return

				# Check if user is automatically subscribed
				if db_pingGroup.steam_id and db_user.steam_id:
					steam_user = self.steam.getUser(db_user.steam_id)
					if db_pingGroup.steam_id in [game.id for game in steam_user.games]:
						summary.set_field('User already subscribed', f'User `{ctx.author.name}` ({ctx.author.id}) already subscribed to ping group `{db_pingGroup.name}` ({db_pingGroup.id})')
						log.warning(f'User `{ctx.author.name}` ({ctx.author.id}) already subscribed to ping group `{db_pingGroup.name}` ({db_pingGroup.id})')
						return

				# Subscribe user to ping group
				db_user.whitelisted_pings.append(db_pingGroup.id)

			# Cleanup
			log.info(f'User `{ctx.author.name}` ({ctx.author.id}) subscribed to ping group `{db_pingGroup.name}` ({db_pingGroup.id})')
			summary.set_header(f'Succesfully subscribed to ping group `{db_pingGroup.name}`')

	@ping.command(name='unsubscribe', description='Unsubscribe from a ping group')
	@utility.signature_command(usage='<(long-string) name> [--quiet | --verbose]')
	async def unsubscribe(self, ctx: commands.Context, dialog: utility.Dialog, summary: utility.Summary, params: dict[str, Any], flags: list[str], vars: dict[str, Any]) -> None:

		# Update ping groups
		if 'quiet' not in flags:
			await dialog.set('DoSsing the Steam API...')
		await self.update_pings(summary)

		# Subscribe to ping group
		with pony.db_session:

			# Find ping group
			unsubscribed = False
			db_user = entities.User.get(discord_id=ctx.author.id)
			db_pingGroup = await self.find_pinggroup(' '.join(params['name']), dialog, summary)
			if not db_pingGroup:
				return
			
			# Check if pingroup is already blacklisted
			if db_pingGroup.id in db_user.blacklisted_pings:
				log.info(f'User `{ctx.author.name}` ({ctx.author.id}) already blacklisted ping group `{db_pingGroup.name}` ({db_pingGroup.id})')
				summary.set_header(f'User already blacklisted `{db_pingGroup.name}`')
				return

			# Check if user is manually subscribed
			if db_pingGroup.id in db_user.whitelisted_pings:
				db_user.whitelisted_pings.remove(db_pingGroup.id)
				log.info(f'User `{ctx.author.name}` ({ctx.author.id}) unsubscribed from ping group `{db_pingGroup.name}` ({db_pingGroup.id})')
				summary.set_header(f'User succesfully unsubscribed from `{db_pingGroup.name}`')
				unsubscribed = True

			# Check if user is automatically subscribed
			if db_pingGroup.steam_id and db_user.steam_id:
				steam_user = self.steam.getUser(db_user.steam_id)
				if db_pingGroup.steam_id in [game.id for game in steam_user.games]:
					db_user.blacklisted_pings.append(db_pingGroup.id)
					log.info(f'User `{ctx.author.name}` ({ctx.author.id}) blacklisted ping group `{db_pingGroup.name}` ({db_pingGroup.id})')
					summary.set_header(f'User succesfully blacklisted `{db_pingGroup.name}`')
					unsubscribed = True

			# Check if user was subscribed in the first place
			if not unsubscribed:
				log.warning(f'User `{ctx.author.name}` ({ctx.author.id}) was never subscribed ping group `{db_pingGroup.name}` ({db_pingGroup.id})')
				summary.header(f'User was never subscribed to `{db_pingGroup.name}`')

	@ping.command(name='add', description='Add a ping group')
	@utility.signature_command(usage='<(long-string) name> [--quiet | --verbose]')
	async def add(self, ctx: commands.Context, dialog: utility.Dialog, summary: utility.Summary, params: dict[str, Any], flags: list[str], vars: dict[str, Any]) -> None:

		# Update pings
		if 'quiet' not in flags:
			await dialog.set('DoSsing the Steam API...')
		await self.update_pings(summary)

		# Search ping groups
		with pony.db_session:
			name = ' '.join(params['name'])

			if pinggroups := list(entities.PingGroup.select()):
				options = []
				for pg in pinggroups:
					options.append(utility.SearchItem(pg, pg.name))
				conclusive, results = utility.fuzzy_search(options, name)

				# If conclusive, there is another ping group with a conflicting name
				if conclusive:
					summary.set_header('Failed to create ping group')
					summary.set_field('Conflicting name', f'There already is a similar ping group with the name `{results[0].text}`. If your new ping group targets a different audience, try giving it a different name. Stupid.')
					log.warn(f'Failed to create ping group by name of `{name}` due to conflicting ping group `{results[0].text}`')
					return

			# Create new ping group
			pingGroup = entities.PingGroup(name=name, aliases=[])

		log.info(f'Created new ping group `{pingGroup.name}` ({pingGroup.id}) at the request of user `{ctx.author.name}` ({ctx.author.id})')
		summary.set_header(f'Successfully created ping group `{pingGroup.name}`')

	@ping.command(name='delete', description='Delete a ping group')
	@utility.signature_command(usage='<(long-string) name> [--quiet | --verbose]')
	@utility.dev_only()
	async def delete(self, ctx: commands.Context, dialog: utility.Dialog, summary: utility.Summary, params: dict[str, Any], flags: list[str], vars: dict[str, Any]) -> None:

		# Update pings
		if 'quiet' not in flags:
			await dialog.set('DoSsing the Steam API...')
		await self.update_pings(summary)

		with pony.db_session:

			# Find ping group
			db_pingGroup = await self.find_pinggroup(' '.join(params['name']), dialog, summary)
			if not db_pingGroup:
				return

			# Check if ping group is implicit
			if db_pingGroup.steam_id:
				summary.set_header('Failed to delete implicit ping group')
				summary.set_field('Failed to delete', f'Ping group `{db_pingGroup.name}` is implicitly created from a Steam library, and thus cannot be deleted.')
				log.warn(f'Ping group `{db_pingGroup.name}` is implicitly created from a Steam library, and thus cannot be deleted.')
				return

			# Delete ping group
			for db_user in pony.select(db_user for db_user in entities.User):
				if db_pingGroup.id in db_user.whitelisted_pings:
					db_user.whitelisted_pings.remove(db_pingGroup.id)

				if db_pingGroup.id in db_user.blacklisted_pings:
					db_user.blacklisted_pings.remove(db_pingGroup.id)

			log.info(f'Successfully deleted ping group `{db_pingGroup.name}` ({db_pingGroup.id})')
			summary.set_header(f'Successfully deleted ping group `{db_pingGroup.name}`')
			db_pingGroup.delete()

	@ping.command(name='alias', description='Add/remove an alias to a ping group')
	@utility.signature_command(usage='<(long-string) name> <(str) --add=alias / (str) --remove=alias> [--quiet | --verbose]')
	async def alias(self, ctx: commands.Context, dialog: utility.Dialog, summary: utility.Summary, params: dict[str, Any], flags: list[str], vars: dict[str, Any]) -> None:
		
		# Update pings
		if 'quiet' not in flags:
			await dialog.set('DoSsing the Steam API...')
		await self.update_pings(summary)

		# Find ping group
		with pony.db_session:
			db_pingGroup = await self.find_pinggroup(' '.join(params['name']), dialog, summary)
			if not db_pingGroup:
				return

			# Add alias
			if 'add' in vars:
				db_pingGroup.aliases.append(vars['add'])
				summary.set_field('Alias added', f'Successfully added alias `{vars["add"]}` to ping group `{db_pingGroup.name}`')
				log.info(f'Added alias `{vars["add"]}` to ping group `{db_pingGroup.name}` ({db_pingGroup.id})')

			# Remove alias
			if 'remove' in vars:
				if vars['remove'] in db_pingGroup.aliases:
					db_pingGroup.aliases.remove(vars['remove'])
					summary.set_field('Alias removed', f'Successfully removed alias `{vars["remove"]}` from ping group `{db_pingGroup.name}`')
					log.info(f'Removed alias `{vars["remove"]}` from ping group `{db_pingGroup.name}` ({db_pingGroup.id})')

				else:
					summary.set_field('Alias not found', f'Alias `{vars["remove"]}` is not an alias of ping group `{db_pingGroup.name}`')
					log.warn(f'Failed to remove alias `{vars["remove"]}` from ping group `{db_pingGroup.name}` ({db_pingGroup.id})')
			
			summary.set_header(f'Aliases modified for ping group `{db_pingGroup.name}`')

	@ping.command(name='info', description='Lists info about users and ping groups')
	@utility.signature_command(usage='[(str) --user=mention | (str) --group=name] [--quiet | --verbose]', thesaurus={'user': ['u'], 'group': ['g']})
	async def info(self, ctx: commands.Context, dialog: utility.Dialog, summary: utility.Summary, params: dict[str, Any], flags: list[str], vars: dict[str, Any]) -> None:
		
		# Update pings
		if 'quiet' not in flags:
			await dialog.set('DoSsing the Steam API...')
		await self.update_pings(summary)

		# Pingroup info
		if 'group' in vars:
			log.debug(f'Following group branch for {ctx.prefix}{ctx.command}')

			with pony.db_session:

				# Find ping group
				db_pingGroup = await self.find_pinggroup(vars['group'], dialog, summary)
				if not db_pingGroup:
					return
				
				steam_game = self.steam.getGame(db_pingGroup.steam_id) if db_pingGroup.steam_id else None
				
				# Find subscribers
				subscribers = []
				for db_user in entities.User.select():
					if db_pingGroup.id in db_user.whitelisted_pings:
						subscribers.append(ctx.guild.get_member(db_user.discord_id))

					elif db_user.steam_id and db_pingGroup.steam_id and db_pingGroup.id not in db_user.blacklisted_pings:
						steam_user = self.steam.getUser(db_user.steam_id)
						if db_pingGroup.steam_id in [game.id for game in steam_user.games]:
							subscribers.append(ctx.guild.get_member(db_user.discord_id))

				# Build info message
				summary.set_header(f'Info for `{db_pingGroup.name}`')
				if steam_game:
					summary.set_field('SteamID', f'Ping group is implicitly created from Steam game {steam_game.link}')
				if db_pingGroup.aliases:
					summary.set_field('Aliases', '\n'.join(db_pingGroup.aliases))
				summary.set_field('Subscribers', '\n'.join([f'`{user.display_name}`' for user in subscribers]) if subscribers else 'No subscribers')

		# User info
		else:
			with pony.db_session:
				if 'user' in vars:
					log.debug(f'Following user branch for {ctx.prefix}{ctx.command}')
					discord_user = await ctx.guild.fetch_member(utility.id_from_mention(vars['user']))
					
				else:
					log.debug(f'Following author branch for {ctx.prefix}{ctx.command}')
					discord_user = ctx.author

				db_user = entities.User.get(discord_id=discord_user.id)
				steam_user = self.steam.getUser(db_user.steam_id) if db_user.steam_id else None

				# Find subscriptions
				subscriptions = [pg.name for pg in entities.PingGroup.select(lambda pg: pg.id in db_user.whitelisted_pings)]

				# Find blacklists
				blacklists = [pg.name for pg in entities.PingGroup.select(lambda pg: pg.id in db_user.blacklisted_pings)]

				# Build info message
				summary.set_header(f'Info for `{discord_user.display_name}`')
				summary.set_field('SteamID', f'Steam account `{steam_user.name}` linked to user. They are implicitly subscribed to all games in their library, unless explicitly blacklisted.' if steam_user else 'No Steam account linked')
				summary.set_field('Subscriptions', '\n'.join(subscriptions) if subscriptions else 'No subscriptions')
				summary.set_field('Blacklisted groups', '\n'.join(blacklists) if blacklists else 'No blacklists')
		
		flags.append('verbose')
