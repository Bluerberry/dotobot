
# Native libraries
import json, logging, os
from logging.config import dictConfig

# External libraries
import dotenv, discord
import pony.orm as pony
from discord.ext import commands

# Local libraries
from lib import entities, utility


# ---------------------> Setup


# Logging
with open('logConfig.json') as file:
	dictConfig(json.load(file))
log = logging.getLogger('root')

# Environment variables
dotenv.load_dotenv()

# Database
entities.db.bind(provider='postgres', user=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD'),
				 host=os.getenv('DB_HOST'), port=os.getenv('DB_PORT'), database=os.getenv('DB_NAME'))
entities.db.generate_mapping(check_tables=True, create_tables=True)

# Discord bot
bot = commands.Bot(command_prefix='$', intents=discord.Intents.all()) # TODO import prefix from settings


# ---------------------> Main


if __name__ == '__main__':

	# Load all extensions
	with pony.db_session:
		for ext in utility.yield_extensions(prefix_path=True):
			try:

				# Skip extensions marked inactive
				name = utility.extension_name(ext)
				if entities.Extension.exists(name=name):
					extension = entities.Extension.get(name=name)
					if not extension.active:
						log.warning(f'Skipped loading inactive extension `{name}`')
						continue

				# Load extension
				bot.load_extension(ext)

			except Exception as err:
				log.error(err)

	bot.run(os.getenv('DISCORD_TOKEN'))
