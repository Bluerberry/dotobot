
from __future__ import annotations

# Native imports
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Literal
from functools import singledispatchmethod as overload

# Local imports
from . import typecasting, errors, tokenizer, signature

# Constants
DEFAULT_COMMAND_OPERATORS = {
	'flag-indicator': '--',
	'variable-indicator': '=',
	'long-parameter-indicator': '"'
	}


# ---------------------> Dataclasses


class Token:
	...

@dataclass
class Parameter(Token):
	value      : Any
	value_type : Literal['str', 'int', 'float', 'bool']

	def fits(self, slot: signature.Parameter) -> bool:
		"""Checks if the parameter fits the slot."""

		return slot.value_type == 'any' or slot.value_type == self.value_type

@dataclass
class Flag(Token):
	key : str

	def fits(self, slot: signature.Flag) -> bool:
		"""Checks if the flag fits the slot."""

		return slot.key == self.key

@dataclass
class Variable(Token):
	key        : str
	value      : Any
	value_type : Literal['str', 'int', 'float', 'bool']

	def fits(self, slot: signature.Variable) -> bool:
		"""Checks if the variable fits the slot."""

		return slot.key == self.key and (slot.value_type == 'any' or slot.value_type == self.value_type)


# ---------------------> Classes


class Command:
	def __init__(self, raw: str, operators: dict[str, str] = {}, thesaurus: dict[str, list[str]] = {}) -> None:

		# Declare variables
		self.raw        : str = raw
		self.thesaurus  : dict[str, list[str]] = thesaurus
		self.parameters : list[Parameter] = []
		self.flags      : list[Flag]      = []
		self.variables  : list[Variable]  = []
		self.operators  : dict[str, str] = deepcopy(DEFAULT_COMMAND_OPERATORS)
		self.operators.update(operators)


		# Parse
		tokens = tokenizer.tokenize(self.raw, self.operators)
		self.__parse_command(tokens)

	def __get_synonym(self, key: str) -> str:
		"""Returns the synonym of a key from a thesaurus."""

		for synonym, keys in self.thesaurus.items():
			if key in keys:
				return synonym
		return key

	def __parse_command(self, tokens: list[tokenizer.Token]) -> None:
		"""Parses the tokens of user input into parameters, flags and variables."""

		while tokens:
			token = tokens.pop(0)
			if type(token) == tokenizer.Operator:

				# Handle flag operator
				if token.operator == 'flag-indicator':

					# Collect key
					if not tokens:
						raise errors.ExpectedTokenError()
					token = tokens.pop(0)
					if type(token) == tokenizer.Operator:
						raise errors.ExpectedTokenError()
					key = self.__get_synonym(token.raw)

					# Handle variable flag
					if tokens and type(tokens[0]) == tokenizer.Operator and tokens[0].operator == 'variable-indicator':
						tokens.pop(0) # Consume variable-indicator

						# Collect value
						if not tokens:
							raise errors.ExpectedTokenError()
						token = tokens.pop(0)
						if type(token) == tokenizer.Operator:
							raise errors.ExpectedTokenError()
						value = token.raw

						# Make variable
						value, value_type = typecasting.cast(value)
						self.variables.append(Variable(key, value, value_type))
						continue

					# Make flag
					self.flags.append(Flag(key))

				# Handle unknown operators
				else:
					raise errors.UnknownOperatorError(token.operator)

			# Handle parameter
			elif type(token) == tokenizer.Token:
				value, value_type = typecasting.cast(token.raw)
				self.parameters.append(Parameter(value, value_type))
			
			# Handle unknown tokens
			else:
				raise errors.UnknownObjectError(token)

	def override(self, command: Command) -> None:
		"""Overrides the parameters, flags and variables of the command with the parameters, flags and variables of another command."""

		self.parameters = command.parameters
		self.flags      = command.flags
		self.variables  = command.variables

	@overload
	def remove(self, obj: Any) -> None:
		"""Remove a parameter, flag or variable from the command."""

		raise TypeError(f'Expected Parameter, Flag or Variable, got {type(obj)}')

	@remove.register
	def _(self, obj: Parameter) -> None:
		self.parameters.remove(obj)

	@remove.register
	def _(self, obj: Flag) -> None:
		self.flags.remove(obj)

	@remove.register
	def _(self, obj: Variable) -> None:
		self.variables.remove(obj)