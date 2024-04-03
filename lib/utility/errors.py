
class WrapperError(Exception):
	def __init__(self):
		super().__init__(f"Incorrect wrapper use")

class UnknownANSIStrokeError(Exception):
	def __init__(self):
		super().__init__(f"Unknown ANSI stroke given")

class UnknownANSIColourError(Exception):
	def __init__(self):
		super().__init__(f"Unknown ANSI colour given")