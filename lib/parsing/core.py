
from __future__ import annotations

from enum import Enum
from typing import Any

import errors


class Types(Enum):
	ANY     = 0
	STRING  = 1
	INTEGER = 2
	FLOAT   = 3
	BOOLEAN = 4

	@staticmethod
	def get_type(raw: str) -> Types:
		if raw in ('any', 'any-array'):
			return Types.ANY
		elif raw in ('str', 'str-array'):
			return Types.STRING
		elif raw in ('int', 'int-array'):
			return Types.INTEGER
		elif raw in ('float', 'float-array'):
			return Types.FLOAT
		elif raw in ('bool', 'bool-array'):
			return Types.BOOLEAN
		else:
			raise errors.UnknownType(raw)
		
	@staticmethod
	def get_array(raw: str) -> bool:
		return raw.endswith('-array')

	@staticmethod
	def convert(raw: str) -> tuple[Any, Types]:
		try:
			if '.' in raw:
				return float(raw), Types.FLOAT
			else:
				return int(raw), Types.INTEGER

		except ValueError:
			if raw.lower() == 'true':
				return True, Types.BOOLEAN
			elif raw.lower() == 'false':
				return False, Types.BOOLEAN
			else:
				return raw, Types.STRING

class Token:
	def __init__(self, raw: str) -> None:
		self.raw = raw

	def __eq__(self, other: object) -> bool:
		if isinstance(other, Token):
			return self.raw == other.raw
		return False

class Operator(Token):
	def __init__(self, raw: str, type: str) -> None:
		self.type = type
		self.raw = raw

	def __eq__(self, other: object) -> bool:
		if isinstance(other, Operator):
			return self.type == other.type
		return False


def tokenize(raw: str, dictionary: dict[str, str]) -> list[Token]:
	tokens = []
	token = ''
	index = 0

	while index < len(raw):

		# Match long parameter
		if raw[index] == dictionary['long-parameter-indicator']:
			if token:
				tokens.append(Token(token))
				token = ''

			index += 1
			if index >= len(raw):
				raise errors.UnexpectedEOF()
			
			while raw[index] != dictionary['long-parameter-indicator']:
				token += raw[index]
				index += 1
				if index >= len(raw):
					raise errors.UnexpectedEOF()
			
			if not token:
				raise errors.UnexpectedToken(dictionary['long-parameter-indicator'])
			tokens.append(Token(token))
			token = ''

			index += 1
			continue

		# Consume whitespace
		if raw[index] == ' ':
			if token:
				tokens.append(Token(token))
				token = ''

			index += 1
			continue

		# Match operator
		match, longest_operator = None, 0
		for type, operator in dictionary.items():
			if raw[index:].startswith(operator) and len(operator) > longest_operator:
				match, longest_operator = type, len(operator)

		if match:
			if token:
				tokens.append(Token(token))
				token = ''

			tokens.append(Operator(dictionary[match], match))
			index += longest_operator
			continue

		# Match parameter
		token += raw[index]
		index += 1

	if token:
		tokens.append(Token(token))
	return tokens
