
class GameNotFoundError(Exception):
	def __init__(self):
		super().__init__(f"Game could not be found")

class UserNotFoundError(Exception):
	def __init__(self):
		super().__init__(f"User could not be found")

class TokenRequiredError(Exception):
	def __init__(self):
		super().__init__(f"API key is required")
