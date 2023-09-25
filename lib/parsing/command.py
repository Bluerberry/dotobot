
from typing import Any

import core
import errors
import signature


class Parameter(core.Token):
	def __init__(self, value: Any, type: core.Types) -> None:
		self.value = value
		self.type = type

	def __eq__(self, other: object) -> bool:
		if isinstance(other, Parameter):
			return self.value == other.value and self.type == other.type
		elif isinstance(other, signature.Parameter):
			return self.type == core.Types.ANY or other.type == core.Types.ANY or self.type == other.type
		return False

class Flag(core.Token):
	def __init__(self, label: str) -> None:
		self.label = label

	def __eq__(self, other: object) -> bool:
		if isinstance(other, (signature.Flag, Flag)):
			return self.label == other.label
		return False

class Variable(core.Token):
	def __init__(self, label: str, value: Any, type: core.Types) -> None:
		self.type = type
		self.label = label
		self.value = value

	def __eq__(self, other: object) -> bool:
		if isinstance(other, Variable):
			return self.label == other.label and self.value == other.value and self.type == other.type
		elif isinstance(other, signature.Variable):
			return self.label == other.label and (self.type == core.Types.ANY or other.type == core.Types.ANY or self.type == other.type)
		return False

def validate_command_tokens(tokens: list[core.Token]) -> None:
	allow_token              = True
	allow_variable_seperator = False
	allow_flag_indicator     = True
	variable_possible        = False
	expect_something         = False

	for token in tokens:
		if isinstance(token, core.Operator):
			if token.type == 'flag-indicator':
				if not allow_flag_indicator:
					raise errors.UnexpectedToken(token)

				# Enforce token structure
				allow_token              = True
				allow_variable_seperator = False
				allow_flag_indicator     = False
				variable_possible        = True
				expect_something         = True

			elif token.type == 'variable-indicator':
				if not allow_variable_seperator:
					raise errors.UnexpectedToken(token)

				# Enforce token structure
				allow_token              = True
				allow_variable_seperator = False
				allow_flag_indicator     = False
				variable_possible        = False
				expect_something         = True

			else:
				raise errors.UnknownOperator(token)

		elif isinstance(token, core.Token):
			if not allow_token:
				raise errors.UnexpectedToken(token)

			# Enforce token structure
			allow_token              = True
			allow_variable_seperator = variable_possible
			allow_flag_indicator     = True
			variable_possible        = False
			expect_something         = False

		else:
			raise errors.UnknownObject(token)

	if expect_something:
		raise errors.UnexpectedEOF()

def parse_command_tokens(tokens: list[core.Token]) -> list[core.Token]:
	if not tokens:
		return []

	parameters, other = [], []
	index = 0

	while index < len(tokens):
		if isinstance(tokens[index], core.Operator):
			if tokens[index].type == 'flag-indicator':

				# Collect variable
				if index + 2 < len(tokens) and isinstance(tokens[index + 2], core.Operator) and tokens[index + 2].type == 'variable-indicator':
					value, type = core.Types.convert(tokens[index + 3].raw)
					other.append(Variable(tokens[index + 1], value, type))
					index += 4

				# Collect flag
				else:
					other.append(Flag(tokens[index + 1]))
					index += 2
		
		# Collect parameter
		else:
			value, type = core.Types.convert(tokens[index].raw)
			parameters.append(Parameter(value, type))
			index += 1

	return parameters + other

def command(raw: str, dictionary: dict[str, str]) -> list[core.Token]:
	tokens = core.tokenize(raw, dictionary)
	validate_command_tokens(tokens)
	return parse_command_tokens(tokens)