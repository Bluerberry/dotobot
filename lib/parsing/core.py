
from __future__ import annotations

# Native libraries
from enum import Enum
from typing import Any

# Local libraries
from . import errors


# ---------------------> Internal Classes


class _Types(Enum):
	ANY     = 0
	STRING  = 1
	INTEGER = 2
	FLOAT   = 3
	BOOLEAN = 4

	@staticmethod
	def get_type(raw: str) -> _Types:
		if raw in ('any', 'any-array'):
			return _Types.ANY
		elif raw in ('str', 'str-array'):
			return _Types.STRING
		elif raw in ('int', 'int-array'):
			return _Types.INTEGER
		elif raw in ('float', 'float-array'):
			return _Types.FLOAT
		elif raw in ('bool', 'bool-array'):
			return _Types.BOOLEAN
		else:
			raise errors.UnknownTypeError(raw)

	@staticmethod
	def is_array(raw: str) -> bool:
		return raw.endswith('-array')

	@staticmethod
	def convert(raw: str) -> tuple[Any, _Types]:
		try:
			if '.' in raw:
				return float(raw), _Types.FLOAT
			else:
				return int(raw), _Types.INTEGER

		except ValueError:
			if raw.lower() == 'true':
				return True, _Types.BOOLEAN
			elif raw.lower() == 'false':
				return False, _Types.BOOLEAN
			else:
				return raw, _Types.STRING

class _Token:
	def __init__(self, raw: str) -> None:
		self.raw = raw

	def __eq__(self, other: object) -> bool:
		if isinstance(other, _Token):
			return self.raw == other.raw
		return False

class _Operator(_Token):
	def __init__(self, raw: str, type: str) -> None:
		self.type = type
		self.raw = raw

	def __eq__(self, other: object) -> bool:
		if isinstance(other, _Operator):
			return self.type == other.type
		return False


# ---------------------> Internal Functions


def _tokenize(raw: str, dictionary: dict[str, str]) -> list[_Token]:
	tokens = []
	token = ''
	index = 0

	while index < len(raw):

		# Match long parameter
		if raw[index] == dictionary['long-parameter-indicator']:
			if token:
				tokens.append(_Token(token))
				token = ''

			index += 1
			if index >= len(raw):
				raise errors.UnexpectedEOFError()

			while raw[index] != dictionary['long-parameter-indicator']:
				token += raw[index]
				index += 1
				if index >= len(raw):
					raise errors.UnexpectedEOFError()

			if not token:
				raise errors.UnexpectedTokenError(dictionary['long-parameter-indicator'])
			tokens.append(_Token(token))
			token = ''

			index += 1
			continue

		# Consume whitespace
		if raw[index] == ' ':
			if token:
				tokens.append(_Token(token))
				token = ''

			index += 1
			continue

		# Match operator
		match, longest_operator = None, 0
		for name, operator in dictionary.items():
			if raw[index:].startswith(operator) and len(operator) > longest_operator:
				match, longest_operator = name, len(operator)

		if match:
			if token:
				tokens.append(_Token(token))
				token = ''

			tokens.append(_Operator(dictionary[match], match))
			index += longest_operator
			continue

		# Match parameter
		token += raw[index]
		index += 1

	if token:
		tokens.append(_Token(token))
	return tokens
