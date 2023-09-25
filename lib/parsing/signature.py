
import command
import core
import errors


class Parameter(core.Token):
	def __init__(self, label: str, required: bool, type: core.Types, array: bool) -> None:
		self.required = required
		self.label = label
		self.array = array
		self.type = type

	def __eq__(self, other: object) -> bool:
		if isinstance(other, Parameter):
			return self.label == other.label and self.required == other.required and self.type == other.type and self.array == other.array
		elif isinstance(other, command.Parameter):
			return self.type == core.Types.ANY or other.type == core.Types.ANY or self.type == other.type
		return False

class Flag(core.Token):
	def __init__(self, label: str, required: bool) -> None:
		self.required = required
		self.label = label

	def __eq__(self, other: object) -> bool:
		if isinstance(other, Flag):
			return self.label == other.label and self.required == other.required
		if isinstance(other, command.Flag):
			return self.label == other.label
		return False

class Variable(core.Token):
	def __init__(self, label: str, description: str, required: bool, type: core.Types) -> None:
		self.description = description
		self.required = required
		self.label = label
		self.type = type

	def __eq__(self, other: object) -> bool:
		if isinstance(other, Variable):
			return self.label == other.label and self.description == other.description and self.required == other.required and self.type == other.type
		if isinstance(other, command.Variable):
			return self.label == other.label and (self.type == core.Types.ANY or other.type == core.Types.ANY or self.type == other.type)
		return False

class Group(core.Token):
	def __init__(self, tokens: list[core.Token], required: bool, exclusive: bool) -> None:
		self.exclusive = exclusive
		self.required = required
		self.tokens = tokens

	def __eq__(self, other: object) -> bool:
		if isinstance(other, Group):
			return self.tokens == other.tokens and self.required == other.required and self.exclusive == other.exclusive
		return False

def validate_signature_tokens(tokens: list[core.Token]) -> None:
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
		if isinstance(token, core.Operator):
			if token.type == 'open-required-group':
				if not allow_open_required_group:
					raise errors.UnexpectedToken(token)

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
					raise errors.UnexpectedToken(token)

				# Enforce bracket structure
				if not len(brackets):
					raise errors.UnmatchedBrackets()
				if brackets[-1] == 'optional':
					raise errors.WeavedBrackets()
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
					raise errors.UnexpectedToken(token)

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
					raise errors.UnexpectedToken(token)

				# Enforce bracket structure
				if not len(brackets):
					raise errors.UnmatchedBrackets()
				if brackets[-1] == 'required':
					raise errors.WeavedBrackets()
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
					raise errors.UnexpectedToken(token)

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
					raise errors.UnexpectedToken(token)

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
					raise errors.UnexpectedToken(token)

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
					raise errors.UnexpectedToken(token)

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
					raise errors.UnexpectedToken(token)

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
				raise errors.UnknownOperator(token)

		elif isinstance(token, core.Token):
			if not allow_token:
				raise errors.UnexpectedToken(token)

			# Check for valid type
			if type_group:
				core.Types.get_type(token.raw)

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
			raise errors.UnknownObject(token)

	if len(brackets):
		raise errors.UnmatchedBrackets()
	if expect_something:
		raise errors.UnexpectedEOF()

def parse_signature_tokens(tokens: list[core.Token], required: bool = True) -> core.Token | None:
	if not tokens:
		return None

	non_exclusive = [] # Non-exclusive groups are seperated by spaces/operators
	exclusive     = [] # Exclusive groups are seperated by xor
	object_type, object_array = core.Types.ANY, False
	index = 0

	while index < len(tokens):
		if isinstance(tokens[index], core.Operator):

			# Collect type
			if tokens[index].type == 'open-type':
				object_type = core.Types.get_type(tokens[index + 1].raw)
				object_array = core.Types.get_array(tokens[index + 1].raw)
				index += 3

			# Collect internal tokens and recurse
			elif tokens[index].type == 'open-required-group':
				index += 1
				brackets = 1
				internal_tokens = []

				while True:
					if isinstance(tokens[index], core.Operator):
						if tokens[index].type == 'open-required-group':
							brackets += 1
						elif tokens[index].type == 'close-required-group':
							brackets -= 1
							if not brackets:
								break

					internal_tokens.append(tokens[index])
					index += 1

				non_exclusive.append(parse_signature_tokens(internal_tokens, True))
				index += 1

			# Collect internal tokens and recurse
			elif tokens[index].type == 'open-optional-group':
				index += 1
				brackets = 1
				internal_tokens = []

				while True:
					if isinstance(tokens[index], core.Operator):
						if tokens[index].type == 'open-optional-group':
							brackets += 1
						elif tokens[index].type == 'close-optional-group':
							brackets -= 1
							if not brackets:
								break

					internal_tokens.append(tokens[index])
					index += 1

				non_exclusive.append(parse_signature_tokens(internal_tokens, False))
				index += 1

			# Add non-exclusive group to exclusive, collapsing single member groups
			elif tokens[index].type == 'xor-seperator':
				exclusive.append(Group(non_exclusive, required, False) if len(non_exclusive) > 1 else non_exclusive[0])
				non_exclusive = []
				index += 1

			# Collect Variable or Flag
			elif tokens[index].type == 'flag-indicator':

				# Variable
				if index + 2 < len(tokens) and isinstance(tokens[index + 2], core.Operator) and tokens[index + 2].type == 'variable-indicator':
					non_exclusive.append(Variable(tokens[index + 1].raw, tokens[index + 3].raw, True, object_type))
					object_type, object_array = core.Types.ANY, False
					index += 4

				# Flag
				else:
					non_exclusive.append(Flag(tokens[index + 1].raw, True))
					index += 2

		# Collect Parameter
		else:
			non_exclusive.append(Parameter(tokens[index].raw, True, object_type, object_array))
			object_type, object_array = core.Types.ANY, False
			index += 1

	# Add non-exclusive group to exclusive, collapsing single member groups
	exclusive.append(Group(non_exclusive, required, False) if len(non_exclusive) > 1 else non_exclusive[0])

	# Return exclusive group
	if len(exclusive) > 1:
		return Group(exclusive, required, True)

	# Return collapsed group, with optional groups taking precedence
	else:
		if required is False:
			exclusive[0].required = False
		return exclusive[0]

def signature(raw: str, dictionary: dict[str, str]) -> core.Token | None:
	tokens = core.tokenize(raw, dictionary)
	validate_signature_tokens(tokens)
	return parse_signature_tokens(tokens)
