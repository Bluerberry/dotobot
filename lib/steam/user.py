
from requests import get as _get

from .game import Game as _Game
from .errors import GameNotFound as _GameNotFound
from .errors import UserNotFound as _UserNotFound

class User:
	def __init__(self, token: str, id64: int, lazy: bool=True) -> None:

		# Get userdata
		site = _get(f'http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?key={token}&steamids={id64}&format=json')
		rawdata = site.json()

		try:
			userdata = rawdata['response']['players'][0]
		except IndexError:
			raise _UserNotFound('The specified user could not be found')

		# Store data
		self.lazy = lazy
		self.raw_userdata = userdata
		self.id64 = int(userdata['steamid'])
		self.name = userdata['personaname']
		self.private = {1: True, 3: False}[userdata['communityvisibilitystate']]

		if self.private:
			return

		# Call steam API for game data
		site = _get(f'http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/?key={token}&steamid={id64}&format=json')
		rawdata = site.json()
		gamedata = rawdata['response']['games']

		# Parse data
		self.raw_gamedata = gamedata
		self.games = []

		for game in gamedata:
			try:
				self.games.append(_Game(game['appid'], lazy))
			except _GameNotFound:
				pass
	
	def unlazify(self) -> None:
		if not self.lazy:
			return

		# Unlazify all games
		for game in self.games:
			try:
				game.unlazify()
			except _GameNotFound:
				self.games.remove(game)

		# Update lazy param
		self.lazy = False
		