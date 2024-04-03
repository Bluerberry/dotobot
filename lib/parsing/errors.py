
class UnknownObjectError(Exception):
	def __init__(self, given_object: str):
		super().__init__(f'Unknown Object({given_object})')

class UnknownOperatorError(Exception):
	def __init__(self, given_operator: str):
		super().__init__(f'Unknown Operator({given_operator})')

class UnexpectedOperatorError(Exception):
	def __init__(self, given_operator_type: str):
		super().__init__(f'Unexpected Operator({given_operator_type})')

class ExpectedOperatorError(Exception):
	def __init__(self, expected_operator_type: str):
		super().__init__(f'Expected Operator({expected_operator_type})')

class ExpectedTokenError(Exception):
	def __init__(self):
		super().__init__(f'Expected Token')

class ExpectedRequiredSlotError(Exception):
	def __init__(self):
		super().__init__(f'Expected required slot')

class RejectedTypeError(Exception):
	def __init__(self, expected_type: str):
		super().__init__(f'Expected token that can accept type {expected_type}')

class UnknownTypeError(Exception):
	def __init__(self, given_type: str):
		super().__init__(f'Unknown Type({given_type})')

class EmptyGroupError(Exception):
	def __init__(self):
		super().__init__(f'Groups cannot be empty')

class MixedSeperatorError(Exception):
	def __init__(self):
		super().__init__(f'Group cannot contain both or and xor seperators')

class NoMatchError(Exception):
	def __init__(self):
		super().__init__(f'No match found')

class TooManyMatchesError(Exception):
	def __init__(self):
		super().__init__(f'Too many matches found')