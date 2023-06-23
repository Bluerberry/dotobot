
from .errors import TokenRequired as _TokenRequired
from .user import User as _User
from .game import Game as _Game

class Client:
	def __init__(self, token: str=None) -> None:
		self.token = token

	def getUser(self, id64: int, lazy: bool=True) -> _User:
		if not self.token:
			raise _TokenRequired('An API token is required to poll userdata')
		return _User(self.token, id64, lazy)

	def getGame(self, id: int, lazy=True) -> _Game:
		return _Game(id, lazy)