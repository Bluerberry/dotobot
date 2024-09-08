
from __future__ import annotations

# Native libraries
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Literal, Tuple
from functools import singledispatchmethod as overload

# Local libraries
from . import errors, tokenizer, typecasting, command

# Constants
DEFAULT_SIGNATURE_OPERATORS = {
	'open-required-group': '<',
	'close-required-group': '>',
	'open-optional-group': '[',
	'close-optional-group': ']',
	'open-type': '(',
	'close-type': ')',
	'flag-indicator': '--',
	'variable-indicator': '=',
	'or-seperator': '/',
	'xor-seperator': '|',
	'long-parameter-indicator': '"'
	}


# ---------------------> Dataclasses


class Token:
	...

@dataclass
class Group(Token):
	group_type : Literal['and', 'or', 'xor']
	tokens     : list[Token]
	required   : bool = True

	def __str__(self) -> str:
		output = f'Group({self.group_type}, {"required" if self.required else "optional"})'
		for token in self.tokens:
			output += '\n  ' + '\n  '.join(str(token).splitlines())
		
		return output

@dataclass
class Parameter(Token):
	key           : str
	value_type    : Literal['str', 'int', 'float', 'bool', 'any']
	is_array      : bool
	is_longstring : bool
	required      : bool = True

	def __str__(self) -> str:
		return f'Parameter({self.key}, {self.value_type}{"-array" if self.is_array else ""}, {"required" if self.required else "optional"})'

@dataclass
class Flag(Token):
	key        : str
	required   : bool = True

	def __str__(self) -> str:
		return f'Flag({self.key}, {"required" if self.required else "optional"})'

@dataclass
class Variable(Token):
	key        : str
	label      : str
	value_type : Literal['str', 'int', 'float', 'bool', 'any']
	required   : bool = True

	def __str__(self) -> str:
		return f'Variable({self.key}, {self.value_type}, {"required" if self.required else "optional"})'

@dataclass
class Matched:
	parameters : dict[str, Any] = field(default_factory=dict)
	flags      : list[str]      = field(default_factory=list)
	variables  : dict[str, Any] = field(default_factory=dict)

	def override(self, matched: Matched) -> None:
		"""Overrides the parameters, flags and variables of the matched object with the parameters, flags and variables of another matched object."""

		self.parameters = matched.parameters
		self.flags      = matched.flags
		self.variables  = matched.variables

	@overload
	def add(self, slot: Any) -> None:
		"""Add a parameter, flag or variable to the matched object."""

		raise TypeError(f'Expected Parameter, Flag or Variable, got {type(slot)}')

	@add.register
	def _(self, slot: Parameter, parameter: command.Parameter | list[command.Parameter]) -> None:
		if type(parameter) == command.Parameter:
			self.parameters[slot.key] = parameter.value
		elif type(parameter) == list:
			self.parameters[slot.key] = [parameter.value for parameter in parameter]
		else:
			raise TypeError(f'Expected Parameter or list, got {type(parameter)}')

	@add.register
	def _(self, flag: command.Flag) -> None:
		self.flags.append(flag.key)

	@add.register
	def _(self, variable: command.Variable) -> None:
		self.variables[variable.key] = variable.value

@dataclass
class Unmatched:
	parameters : list[str]      = field(default_factory=list)
	flags      : list[str]      = field(default_factory=list)
	variables  : dict[str, Any] = field(default_factory=dict)

	@overload
	def add(self, slot: Any) -> None:
		"""Add a parameter, flag or variable to the unmatched object."""

		raise TypeError(f'Expected Parameter, Flag or Variable, got {type(slot)}')

	@add.register
	def _(self, parameter: command.Parameter) -> None:
		self.parameters.append(parameter.value)

	@add.register
	def _(self, flag: command.Flag) -> None:
		self.flags.append(flag.key)

	@add.register
	def _(self, variable: command.Variable) -> None:
		self.variables[variable.key] = variable.value


# ---------------------> Classes


class Signature:
	def __init__(self, raw: str, operators: dict[str, str] = {}) -> None:

		# Declare variables
		self.raw       : str            = raw
		self.signature : Token          = None
		self.operators : dict[str, str] = deepcopy(DEFAULT_SIGNATURE_OPERATORS)
		self.operators.update(operators)

		# Parse
		tokens = tokenizer.tokenize(self.raw, self.operators)
		self.__parse_signature(tokens)

	def __parse_signature(self, tokens: list[tokenizer.Token]) -> None:
		"""Parses the tokens of user input into a signature."""

		def recurse(tokens: list[tokenizer.Token], required: bool) -> Token | None:
			if not tokens:
				return None

			# Assign variables
			expect_typed  = False
			is_array      = False
			is_longstring = False
			object_type   = 'any'
			group_type    = 'and'
			result, group = [], []

			# Parse tokens
			while tokens:
				token = tokens.pop(0)
				if type(token) == tokenizer.Operator:

					# Handle group operators
					if token.operator in ('open-required-group', 'open-optional-group'):
						if expect_typed:
							raise errors.RejectedTypeError(object_type + ('-array' if is_array else ''))

						# Assign variables
						internal_tokens, brackets = [], 1
						is_required = token.operator == 'open-required-group'
						opening_operator = 'open-required-group'  if is_required else 'open-optional-group'
						closing_operator = 'close-required-group' if is_required else 'close-optional-group'

						# Collect group
						while True:
							if not tokens:
								if internal_tokens:
									raise errors.ExpectedOperatorError(closing_operator)
								raise errors.UnexpectedOperatorError(opening_operator)

							token = tokens.pop(0)
							if type(token) == tokenizer.Operator:
								if token.operator == opening_operator:
									brackets += 1
								elif token.operator == closing_operator:
									brackets -= 1
									if not brackets:
										break

							internal_tokens.append(token)

						# Parse group
						if not internal_tokens:
							raise errors.EmptyGroupError()
						group.append(recurse(internal_tokens, is_required)) 

					# Handle type operator
					elif token.operator == 'open-type':
						if expect_typed:
							raise errors.RejectedTypeError(object_type + ('-array' if is_array else ''))
						if not tokens:
							raise errors.UnexpectedOperatorError('open-type')

						# Collect object type
						token = tokens.pop(0)
						if type(token) == tokenizer.Operator and token.operator == 'close-type':
							raise errors.ExpectedTokenError()
						
						# Parse type
						object_type, is_array, is_longstring = typecasting.parse(token.raw)
						expect_typed = True

						# Consume close-type
						if not tokens:
							raise errors.ExpectedOperatorError('close-type')
						token = tokens.pop(0)
						if type(token) == tokenizer.Token or token.operator != 'close-type':
							raise errors.ExpectedOperatorError('close-type')

					# Handle flag operator
					elif token.operator == 'flag-indicator':

						# Collect key
						if not tokens:
							raise errors.ExpectedTokenError()
						token = tokens.pop(0)
						if type(token) == tokenizer.Operator:
							raise errors.ExpectedTokenError()
						key = token.raw

						# Handle variable flag
						if tokens and type(tokens[0]) == tokenizer.Operator and tokens[0].operator == 'variable-indicator':
							tokens.pop(0) # Consume variable-indicator

							# Collect label
							if not tokens:
								raise errors.ExpectedTokenError()
							token = tokens.pop(0)
							if type(token) == tokenizer.Operator:
								raise errors.ExpectedTokenError()
							label = token.raw

							# Make variable
							if is_array:
								raise errors.RejectedTypeError(object_type + '-array')
							group.append(Variable(key, label, object_type))
							object_type, expect_typed = 'any', False
							continue

						# Make flag
						if expect_typed:
							raise errors.RejectedTypeError(object_type + ('-array' if is_array else ''))
						group.append(Flag(key))

					# Handle xor operator
					elif token.operator == 'xor-seperator':
						if expect_typed:
							raise errors.RejectedTypeError(object_type + ('-array' if is_array else ''))
						if group_type == 'or':
							raise errors.MixedSeperatorError()
						if not group:
							raise errors.UnexpectedOperatorError('xor-seperator')
						if not any(slot.required for slot in group):
							raise errors.ExpectedRequiredSlotError()

						# Add group to result
						result.append(Group('and', group, True) if len(group) > 1 else group[0])
						group, group_type = [], 'xor'

					# Handle or operator
					elif token.operator == 'or-seperator':
						if expect_typed:
							raise errors.RejectedTypeError(object_type + ('-array' if is_array else ''))
						if group_type == 'xor':
							raise errors.MixedSeperatorError()
						if not group:
							raise errors.UnexpectedOperatorError('or-seperator')
						if not any(slot.required for slot in group):
							raise errors.ExpectedRequiredSlotError()
						
						# Add group to result
						result.append(Group('and', group, True) if len(group) > 1 else group[0])
						group, group_type = [], 'or'

					# Handle illegal operators
					elif token.operator in ('close-required-group', 'close-optional-group', 'close-type', 'variable-indicator'):
						raise errors.UnexpectedOperatorError(token.operator)

					# Handle unknown operators
					else:
						raise errors.UnknownOperatorError(token.operator)

				# Handle parameter
				elif type(token) == tokenizer.Token:
					group.append(Parameter(token.raw, object_type, is_array, is_longstring))
					object_type, is_array, is_longstring, expect_typed = 'any', False, False, False
				
				# Handle unknown objects
				else:
					raise errors.UnknownObjectError(token)

			# Check if there is unfinished buisness
			if expect_typed:
				raise errors.RejectedTypeError(object_type + ('-array' if is_array else ''))
			if not group:
				raise errors.UnexpectedOperatorError('xor-seperator' if group_type == 'xor' else 'or-seperator')
			
			has_required = any(slot.required for slot in group)
			if result and not has_required:
				raise errors.ExpectedRequiredSlotError()

			# Append last group
			result.append(Group('and', group, has_required) if len(group) > 1 else group[0])

			# Return Group if there is more than one result
			if len(result) > 1:
				return Group(group_type, result, required)

			# Return single result
			result = result[0]
			result.required &= required
			return result

		self.signature = recurse(tokens, True)

	def match(self, cmd: command.Command) -> Tuple[Matched, Unmatched]:
		"""Matches a command to the signature and returns the matched and unmatched parameters, variables and flags."""

		def recurse(slot: Token, cmd: command.Command, matched: Matched) -> bool:

			# Handle parameters
			if type(slot) == Parameter:

				# Handle long strings
				if slot.is_longstring:
					if cmd.parameters:
						matched.add(slot, command.Parameter(' '.join([str(parameter.value) for parameter in cmd.parameters]), 'str'))
						cmd.parameters = []
						return True

				# Handle array parameters
				elif slot.is_array:
					values = []

					while cmd.parameters:
						parameter = cmd.parameters[0]
						if parameter.fits(slot):
							values.append(parameter)
							cmd.remove(parameter)

					if values:
						matched.add(slot, values)
						return True

				# Handle single parameters
				elif cmd.parameters:
					parameter = cmd.parameters[0]	
					if parameter.fits(slot):
						matched.add(slot, parameter)
						cmd.remove(parameter)
						return True

			# Handle flags
			elif type(slot) == Flag:
				for flag in cmd.flags:
					if flag.fits(slot):
						matched.add(flag)
						cmd.remove(flag)
						return True

			# Handle variables
			elif type(slot) == Variable:
				for variable in cmd.variables:
					if variable.fits(slot):
						matched.add(variable)
						cmd.remove(variable)
						return True

			# Handle groups
			elif type(slot) == Group:
				group = slot
				success = False
				recurse_command = deepcopy(cmd)
				recurse_matched = deepcopy(matched)

				for slot in group.tokens:
					if recurse(slot, recurse_command, recurse_matched):
						cmd.override(recurse_command)
						matched.override(recurse_matched)

						if group.group_type == 'xor' and success:
							raise errors.TooManyMatchesError()
						success = True

					elif group.group_type == 'and':
						return not group.required

				return success or not group.required
			
			# Handle unknown objects
			else:
				raise errors.UnknownObjectError(slot)

			# No match
			return not slot.required

		# Match command
		matched = Matched()
		if self.signature:
			if not recurse(self.signature, cmd, matched):
				raise errors.NoMatchError()

		# Collect unmatched
		unmatched = Unmatched()
		for parameter in cmd.parameters:
			unmatched.add(parameter)
		for flag in cmd.flags:
			unmatched.add(flag)
		for variable in cmd.variables:
			unmatched.add(variable)

		return matched, unmatched

