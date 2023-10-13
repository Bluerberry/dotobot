
# Stdlib imports
from typing import Any
from copy import deepcopy

# Local imports
from . import errors, core, signature

# Constants
DEFAULT_DICTIONARY = {
	'flag-indicator':     '--',
	'variable-indicator': '=',
	'long-parameter-indicator': '"'	
}

DEFAULT_THESAURUS = {
    'q': 'quiet',
    'v': 'verbose'
}

# ---------------------> Internal Classes

class _Parameter(core._Token):
	def __init__(self, value: Any, type: core._Types) -> None:
		self.value = value
		self.type = type

	def __eq__(self, other: object) -> bool:
		if isinstance(other, _Parameter):
			return self.value == other.value and self.type == other.type
		elif isinstance(other, signature._Parameter):
			return self.type == core._Types.ANY or other.type == core._Types.ANY or self.type == other.type
		return False

class _Flag(core._Token):
	def __init__(self, label: str) -> None:
		self.label = label

	def __eq__(self, other: object) -> bool:
		if isinstance(other, (signature._Flag, _Flag)):
			return self.label == other.label
		return False

class _Variable(core._Token):
	def __init__(self, label: str, value: Any, type: core._Types) -> None:
		self.type = type
		self.label = label
		self.value = value

	def __eq__(self, other: object) -> bool:
		if isinstance(other, _Variable):
			return self.label == other.label and self.value == other.value and self.type == other.type
		elif isinstance(other, signature._Variable):
			return self.label == other.label and (self.type == core._Types.ANY or other.type == core._Types.ANY or self.type == other.type)
		return False


# ---------------------> External Classes


class Command:
	def __init__(self, raw: str, dictionary: dict[str, str], thesaurus: dict[str, str]) -> None:
		self.dictionary = deepcopy(DEFAULT_DICTIONARY)
		self.dictionary.update(dictionary)
		self.thesaurus = deepcopy(DEFAULT_THESAURUS)
		self.thesaurus.update(thesaurus)
		self.raw = raw

		tokens = core._tokenize(raw, self.dictionary)
		self.__validate_tokens(tokens)
		self.tokens = self.__parse_tokens(tokens)

	def __validate_tokens(self, tokens: list[core._Token]) -> None:
		allow_token              = True
		allow_variable_seperator = False
		allow_flag_indicator     = True
		variable_possible        = False
		expect_something         = False

		for token in tokens:
			if isinstance(token, core._Operator):
				if token.type == 'flag-indicator':
					if not allow_flag_indicator:
						raise errors.UnexpectedTokenError(token)

					# Enforce token structure
					allow_token              = True
					allow_variable_seperator = False
					allow_flag_indicator     = False
					variable_possible        = True
					expect_something         = True

				elif token.type == 'variable-indicator':
					if not allow_variable_seperator:
						raise errors.UnexpectedTokenError(token)

					# Enforce token structure
					allow_token              = True
					allow_variable_seperator = False
					allow_flag_indicator     = False
					variable_possible        = False
					expect_something         = True

				else:
					raise errors.UnknownOperatorError(token)

			elif isinstance(token, core._Token):
				if not allow_token:
					raise errors.UnexpectedTokenError(token)

				# Enforce token structure
				allow_token              = True
				allow_variable_seperator = variable_possible
				allow_flag_indicator     = True
				variable_possible        = False
				expect_something         = False

			else:
				raise errors.UnknownObjectError(token)

		if expect_something:
			raise errors.UnexpectedEOFError()

	def __parse_tokens(self, tokens: list[core._Token]) -> list[core._Token]:
		if not tokens:
			return []

		parameters, other = [], []
		index = 0

		while index < len(tokens):
			if isinstance(tokens[index], core._Operator):
				if tokens[index].type == 'flag-indicator':

					# Collect label
					label = tokens[index + 1].raw
					if label in self.thesaurus:
						label = self.thesaurus[label]

					# Collect variable
					if index + 2 < len(tokens) and isinstance(tokens[index + 2], core._Operator) and tokens[index + 2].type == 'variable-indicator':
						value, type = core._Types.convert(tokens[index + 3].raw)
						other.append(_Variable(label, value, type))
						index += 4

					# Collect flag
					else:
						other.append(_Flag(label))
						index += 2

			# Collect parameter
			else:
				value, type = core._Types.convert(tokens[index].raw)
				parameters.append(_Parameter(value, type))
				index += 1

		return parameters + other
	
	def match(self, signature: signature.Signature) -> signature.MatchResult:
		return signature.match(self.tokens)
