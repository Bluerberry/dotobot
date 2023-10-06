
# Stdlib imports
from typing import Any
from copy import deepcopy

# Local imports
from . import errors, core, command

# Constants
DEFAULT_DICTIONARY = {
	'open-required-group':  	'<',
	'close-required-group': 	'>',
	'open-optional-group':  	'[',
	'close-optional-group': 	']',
	'open-type':            	'(',
	'close-type':           	')',
	'flag-indicator':       	'--',
	'variable-indicator':   	'=',
	'xor-seperator':        	'|',
	'long-parameter-indicator': '"'	
}    


# ---------------------> Internal Classes


class _Parameter(core._Token):
	def __init__(self, label: str, required: bool, type: core._Types, array: bool) -> None:
		self.required = required
		self.label = label
		self.array = array
		self.type = type

	def __eq__(self, other: object) -> bool:
		if isinstance(other, _Parameter):
			return self.label == other.label and self.required == other.required and self.type == other.type and self.array == other.array
		elif isinstance(other, command._Parameter):
			return self.type == core._Types.ANY or other.type == core._Types.ANY or self.type == other.type
		return False

class _Flag(core._Token):
	def __init__(self, label: str, required: bool) -> None:
		self.required = required
		self.label = label

	def __eq__(self, other: object) -> bool:
		if isinstance(other, _Flag):
			return self.label == other.label and self.required == other.required
		if isinstance(other, command._Flag):
			return self.label == other.label
		return False

class _Variable(core._Token):
	def __init__(self, label: str, description: str, required: bool, type: core._Types) -> None:
		self.description = description
		self.required = required
		self.label = label
		self.type = type

	def __eq__(self, other: object) -> bool:
		if isinstance(other, _Variable):
			return self.label == other.label and self.description == other.description and self.required == other.required and self.type == other.type
		if isinstance(other, command._Variable):
			return self.label == other.label and (self.type == core._Types.ANY or other.type == core._Types.ANY or self.type == other.type)
		return False

class _Group(core._Token):
	def __init__(self, tokens: list[core._Token], required: bool, exclusive: bool) -> None:
		self.exclusive = exclusive
		self.required = required
		self.tokens = tokens

	def __eq__(self, other: object) -> bool:
		if isinstance(other, _Group):
			return self.tokens == other.tokens and self.required == other.required and self.exclusive == other.exclusive
		return False


# ---------------------> External Classes


class MatchResult:
	def __init__(self, matched: bool, matched_parameters: dict[str, Any], matched_flags: list[str], matched_variables: dict[str, Any], unmatched_parameters: list[str], unmatched_flags: list[str], unmatched_variables: dict[str, Any]) -> None:
		self.matched              = matched
		self.matched_parameters   = matched_parameters
		self.matched_flags        = matched_flags
		self.matched_variables    = matched_variables
		self.unmatched_parameters = unmatched_parameters
		self.unmatched_flags      = unmatched_flags
		self.unmatched_variables  = unmatched_variables

class Signature:
	def __init__(self, raw: str, dictionary: dict[str, str]) -> None:
		self.raw = raw
		self.dictionary = deepcopy(DEFAULT_DICTIONARY)
		self.dictionary.update(dictionary)

		tokens = core._tokenize(raw, self.dictionary)
		self.__validate_tokens(tokens)
		self.signature = self.__parse_tokens(tokens)

	def __validate_tokens(self, tokens: list[core._Token]) -> None:
		allow_open_required_group   = True
		allow_close_required_group  = False
		allow_open_optional_group   = True
		allow_close_optional_group  = False
		allow_open_type             = True
		allow_close_type            = False
		allow_token                 = True
		allow_variable_seperator    = False
		allow_flag_indicator        = True
		allow_xor                   = False

		expect_something            = False
		variable_possible           = False
		type_group                  = False

		brackets = []

		for token in tokens:
			if isinstance(token, core._Operator):
				if token.type == 'open-required-group':
					if not allow_open_required_group:
						raise errors.UnexpectedTokenError(token)

					# Enforce bracket structure
					brackets.append('required')

					# Enforce token structure
					allow_open_required_group   = True
					allow_close_required_group  = False
					allow_open_optional_group   = True
					allow_close_optional_group  = False
					allow_open_type             = True
					allow_close_type            = False
					allow_token                 = True
					allow_variable_seperator    = False
					allow_flag_indicator        = True
					allow_xor                   = False

					expect_something            = True
					variable_possible           = False
					type_group                  = False

				elif token.type == 'close-required-group':
					if not allow_close_required_group:
						raise errors.UnexpectedTokenError(token)

					# Enforce bracket structure
					if not len(brackets):
						raise errors.UnmatchedBracketsError()
					if brackets[-1] == 'optional':
						raise errors.WeavedBracketsError()
					brackets.pop()

					# Enforce token structure
					allow_open_required_group   = True
					allow_close_required_group  = True
					allow_open_optional_group   = True
					allow_close_optional_group  = True
					allow_open_type             = True
					allow_close_type            = False
					allow_token                 = True
					allow_variable_seperator    = False
					allow_flag_indicator        = True
					allow_xor                   = True

					expect_something            = False
					variable_possible           = False
					type_group                  = False

				elif token.type == 'open-optional-group':
					if not allow_open_optional_group:
						raise errors.UnexpectedTokenError(token)

					# Enforce bracket structure
					brackets.append('optional')

					# Enforce token structure
					allow_open_required_group   = True
					allow_close_required_group  = False
					allow_open_optional_group   = True
					allow_close_optional_group  = False
					allow_open_type             = True
					allow_close_type            = False
					allow_token                 = True
					allow_variable_seperator    = False
					allow_flag_indicator        = True
					allow_xor                   = False

					expect_something            = True
					variable_possible           = False
					type_group                  = False

				elif token.type == 'close-optional-group':
					if not allow_close_optional_group:
						raise errors.UnexpectedTokenError(token)

					# Enforce bracket structure
					if not len(brackets):
						raise errors.UnmatchedBracketsError()
					if brackets[-1] == 'required':
						raise errors.WeavedBracketsError()
					brackets.pop()

					# Enforce token structure
					allow_open_required_group   = True
					allow_close_required_group  = True
					allow_open_optional_group   = True
					allow_close_optional_group  = True
					allow_open_type             = True
					allow_close_type            = False
					allow_token                 = True
					allow_variable_seperator    = False
					allow_flag_indicator        = True
					allow_xor                   = True

					expect_something            = False
					variable_possible           = False
					type_group                  = False

				elif token.type == 'open-type':
					if not allow_open_type:
						raise errors.UnexpectedTokenError(token)

					# Enforce token structure
					allow_open_required_group   = False
					allow_close_required_group  = False
					allow_open_optional_group   = False
					allow_close_optional_group  = False
					allow_open_type             = False
					allow_close_type            = False
					allow_token                 = True
					allow_variable_seperator    = False
					allow_flag_indicator        = False
					allow_xor                   = False

					expect_something            = True
					variable_possible           = False
					type_group                  = True

				elif token.type == 'close-type':
					if not allow_close_type:
						raise errors.UnexpectedTokenError(token)

					# Enforce token structure
					allow_open_required_group   = False
					allow_close_required_group  = False
					allow_open_optional_group   = False
					allow_close_optional_group  = False
					allow_open_type             = False
					allow_close_type            = False
					allow_token                 = True
					allow_variable_seperator    = False
					allow_flag_indicator        = True
					allow_xor                   = False

					expect_something            = True
					variable_possible           = False
					type_group                  = False

				elif token.type == 'flag-indicator':
					if not allow_flag_indicator:
						raise errors.UnexpectedTokenError(token)

					# Enforce token structure
					allow_open_required_group   = False
					allow_close_required_group  = False
					allow_open_optional_group   = False
					allow_close_optional_group  = False
					allow_open_type             = False
					allow_close_type            = False
					allow_token                 = True
					allow_variable_seperator    = False
					allow_flag_indicator        = False
					allow_xor                   = False

					expect_something            = True
					variable_possible           = True
					type_group                  = False

				elif token.type == 'variable-indicator':
					if not allow_variable_seperator:
						raise errors.UnexpectedTokenError(token)

					# Enforce token structure
					allow_open_required_group   = False
					allow_close_required_group  = False
					allow_open_optional_group   = False
					allow_close_optional_group  = False
					allow_open_type             = False
					allow_close_type            = False
					allow_token                 = True
					allow_variable_seperator    = False
					allow_flag_indicator        = False
					allow_xor                   = False

					expect_something            = True
					variable_possible           = False
					type_group                  = False

				elif token.type == 'xor-seperator':
					if not allow_xor:
						raise errors.UnexpectedTokenError(token)

					# Enforce token structure
					allow_open_required_group   = True
					allow_close_required_group  = False
					allow_open_optional_group   = True
					allow_close_optional_group  = False
					allow_open_type             = True
					allow_close_type            = False
					allow_token                 = True
					allow_variable_seperator    = False
					allow_flag_indicator        = True
					allow_xor                   = False

					expect_something            = True
					variable_possible           = False
					type_group                  = False

				else:
					raise errors.UnknownOperatorError(token)

			elif isinstance(token, core._Token):
				if not allow_token:
					raise errors.UnexpectedTokenError(token)

				# Check for valid type
				if type_group:
					core._Types.get_type(token.raw)

				# Enforce token structure
				allow_open_required_group   = not type_group
				allow_close_required_group  = not type_group
				allow_open_optional_group   = not type_group
				allow_close_optional_group  = not type_group
				allow_open_type             = not type_group
				allow_close_type            = type_group
				allow_token                 = not type_group
				allow_variable_seperator    = not type_group and variable_possible
				allow_flag_indicator        = not type_group
				allow_xor                   = not type_group

				expect_something            = type_group
				type_group                  = False
				variable_possible           = False

			else:
				raise errors.UnknownObjectError(token)

		if len(brackets):
			raise errors.UnmatchedBracketsError()
		if expect_something:
			raise errors.UnexpectedEOFError()

	def __parse_tokens(self, tokens: list[core._Token], required: bool = True) -> core._Token | None:
		if not tokens:
			return None

		non_exclusive = [] # Non-exclusive groups are seperated by spaces/operators
		exclusive     = [] # Exclusive groups are seperated by xor
		object_type, object_array = core._Types.ANY, False
		index = 0

		while index < len(tokens):
			if isinstance(tokens[index], core._Operator):

				# Collect type
				if tokens[index].type == 'open-type':
					object_type = core._Types.get_type(tokens[index + 1].raw)
					object_array = core._Types.is_array(tokens[index + 1].raw)
					index += 3

				# Collect internal tokens and recurse
				elif tokens[index].type == 'open-required-group':
					index += 1
					brackets = 1
					internal_tokens = []

					while True:
						if isinstance(tokens[index], core._Operator):
							if tokens[index].type == 'open-required-group':
								brackets += 1
							elif tokens[index].type == 'close-required-group':
								brackets -= 1
								if not brackets:
									break

						internal_tokens.append(tokens[index])
						index += 1

					non_exclusive.append(self.__parse_tokens(internal_tokens, True))
					index += 1

				# Collect internal tokens and recurse
				elif tokens[index].type == 'open-optional-group':
					index += 1
					brackets = 1
					internal_tokens = []

					while True:
						if isinstance(tokens[index], core._Operator):
							if tokens[index].type == 'open-optional-group':
								brackets += 1
							elif tokens[index].type == 'close-optional-group':
								brackets -= 1
								if not brackets:
									break

						internal_tokens.append(tokens[index])
						index += 1

					non_exclusive.append(self.__parse_tokens(internal_tokens, False))
					index += 1

				# Add non-exclusive group to exclusive, collapsing single member groups
				elif tokens[index].type == 'xor-seperator':
					exclusive.append(_Group(non_exclusive, required, False) if len(non_exclusive) > 1 else non_exclusive[0])
					non_exclusive = []
					index += 1

				# Collect Variable or Flag
				elif tokens[index].type == 'flag-indicator':

					# Variable
					if index + 2 < len(tokens) and isinstance(tokens[index + 2], core._Operator) and tokens[index + 2].type == 'variable-indicator':
						non_exclusive.append(_Variable(tokens[index + 1].raw, tokens[index + 3].raw, True, object_type))
						object_type, object_array = core._Types.ANY, False
						index += 4

					# Flag
					else:
						non_exclusive.append(_Flag(tokens[index + 1].raw, True))
						index += 2

			# Collect Parameter
			else:
				non_exclusive.append(_Parameter(tokens[index].raw, True, object_type, object_array))
				object_type, object_array = core._Types.ANY, False
				index += 1

		# Add non-exclusive group to exclusive, collapsing single member groups
		exclusive.append(_Group(non_exclusive, required, False) if len(non_exclusive) > 1 else non_exclusive[0])

		# Return exclusive group
		if len(exclusive) > 1:
			return _Group(exclusive, required, True)

		# Return collapsed group, with optional groups taking precedence
		else:
			if required is False:
				exclusive[0].required = False
			return exclusive[0]

	def match(self, parsed_command) -> MatchResult: # I wish I could type here, but circular imports are the bane of my existance
		matched_parameters   = {}
		matched_flags        = []
		matched_variables    = {}

		unmatched_parameters = []
		unmatched_flags      = []
		unmatched_variables  = {}

		tokens = deepcopy(parsed_command.tokens)

		def internal(signature: core._Token):

			# Recurse into groups
			if isinstance(signature, _Group):
				if signature.exclusive:
					for token in signature.tokens:
						if internal(token):
							return True
					return not signature.required

				else:
					for token in signature.tokens:
						if not internal(token):
							return not signature.required
					return True

			# Matching parameters
			elif isinstance(signature, _Parameter):

				# Check if atleast one parameter matches
				if not tokens or tokens[0] != signature:
					return not signature.required

				# Gather all matching parameters
				if signature.array:
					matched_parameters[signature.label] = []
					while tokens and tokens[0] == signature:
						matched_parameters[signature.label].append(tokens.pop(0).value)

				# Gather first matching parameter
				else:
					matched_parameters[signature.label] = tokens.pop(0).value

				return True

			# Matching flags
			elif isinstance(signature, _Flag):

				# Check if there are flags left
				if not tokens:
					return not signature.required

				# Check if flag matches
				if signature in tokens:
					matched_flags.append(signature.label)
					tokens.remove(signature)
					return True

				return not signature.required

			elif isinstance(signature, _Variable):

				# Check if there are variables left
				if not tokens:
					return not signature.required

				# Check if variable matches
				for token in tokens:
					if token == signature:
						matched_variables[token.label] = token.value
						tokens.remove(token)
						return True

				return not signature.required

		if self.signature:
			matched = internal(self.signature)
		else:
			matched = True

		for token in tokens:
			if isinstance(token, command._Parameter):
				unmatched_parameters.append(token.value)
			elif isinstance(token, command._Flag):
				unmatched_flags.append(token.label)
			elif isinstance(token, command._Variable):
				unmatched_variables[token.label] = token.value

		return MatchResult(matched, matched_parameters, matched_flags, matched_variables, unmatched_parameters, unmatched_flags, unmatched_variables)

