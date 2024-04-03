
# Native imports
from dataclasses import dataclass

# Local libraries
from . import errors


# ---------------------> Classes


@dataclass
class Token:
	raw : str

@dataclass
class Operator(Token):
	raw      : str
	operator : str


# ---------------------> Functions


def tokenize(raw: str, operators: dict[str, str]) -> list[Token]:
	"""Tokenizes a raw string seperated by greedy-matched operators and spaces."""

	index = 0
	tokens = []
	aggregate = ''
	while index < len(raw):

		# Match long parameter
		if raw[index] == operators['long-parameter-indicator']:
			if aggregate:
				tokens.append(Token(aggregate))
				aggregate = ''

			index += 1
			if index >= len(raw):
				raise errors.UnexpectedOperatorError('long-parameter-indicator')

			while raw[index] != operators['long-parameter-indicator']:
				aggregate += raw[index]
				index += 1
				if index >= len(raw):
					raise errors.ExpectedOperatorError('long-parameter-indicator')

			if not aggregate:
				raise errors.EmptyGroupError()
			tokens.append(Token(aggregate))
			aggregate = ''

			index += 1
			continue

		# Consume whitespace
		if raw[index] == ' ':
			if aggregate:
				tokens.append(Token(aggregate))
				aggregate = ''

			index += 1
			continue

		# Match operator
		match, longest_operator = None, 0
		for name, operator in operators.items():
			if raw[index:].startswith(operator) and len(operator) > longest_operator:
				match, longest_operator = name, len(operator)

		if match:
			if aggregate:
				tokens.append(Token(aggregate))
				aggregate = ''

			tokens.append(Operator(operators[match], match))
			index += longest_operator
			continue

		# Match parameter
		aggregate += raw[index]
		index += 1

	if aggregate:
		tokens.append(Token(aggregate))
	return tokens

