
# Local libraries
from . import errors, game, user


# ---------------------> External Classes


class Client:
	def __init__(self, token: str=None) -> None:
		self.token = token

	def getUser(self, id64: int, lazy: bool=True) -> user.User:
		if not self.token:
			raise errors.TokenRequiredError('An API token is required to poll userdata')
		return user.User(self.token, id64, lazy)

	def getGame(self, id: int, lazy=True) -> game.Game:
		return game.Game(id, lazy)