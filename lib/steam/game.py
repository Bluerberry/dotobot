
from requests import get as _get

from .errors import GameNotFound as _GameNotFound

class Game:
	def __init__(self, id: int, lazy: bool=True) -> None:
		self.lazy = lazy
		self.id = id

		# Lazy Game setup
		if self.lazy:
			self.raw_gamedata = { 'steam_appid' : self.id }
			return
		
		# Normal Game setup
		self.unlazify()
	
	def unlazify(self) -> None:
		if not self.lazy:
			return

		# Get appdetails
		site = _get(f'http://store.steampowered.com/api/appdetails?appids={self.id}&format=json')
		rawdata = site.json()

		if not rawdata or not rawdata[str(self.id)]['success']:
			raise _GameNotFound('The specified game could not be found')
		gamedata = rawdata[str(self.id)]['data']

		# Store appdetails
		self.lazy = False
		self.raw_gamedata = gamedata
		self.id = gamedata['steam_appid']
		self.name = gamedata['name']