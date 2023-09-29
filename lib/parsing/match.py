
from typing import Any

import command
import core
import errors
import signature


class MatchResult:
	def __init__(self, matched: bool, matched_parameters: dict[str, Any], matched_flags: list[str], matched_variables: dict[str, Any], unmatched_parameters: list[str], unmatched_flags: list[str], unmatched_variables: dict[str, Any]) -> None:
		self.matched = matched
		self.matched_parameters = matched_parameters
		self.matched_flags = matched_flags
		self.matched_variables = matched_variables
		self.unmatched_parameters = unmatched_parameters
		self.unmatched_flags = unmatched_flags
		self.unmatched_variables = unmatched_variables
	
	def __repr__(self) -> str:
		return f'MatchResult({self.matched}, {self.matched_parameters}, {self.matched_flags}, {self.matched_variables}, {self.unmatched_parameters}, {self.unmatched_flags}, {self.unmatched_variables})'

def match(signature: core.Token, command: list[core.Token]) -> MatchResult:
	matched_parameters   = {}
	matched_flags        = []
	matched_variables    = {}

	unmatched_parameters = []
	unmatched_flags      = []
	unmatched_variables  = {}

	def internal(reference: core.Token):

		# Recurse into groups
		if isinstance(reference, signature.SignatureGroup):
			if reference.exclusive:
				for token in reference.tokens:
					if internal(token):
						return True
				return not reference.required

			else:
				for token in reference.tokens:
					if not internal(token):
						return not reference.required
				return True

		# Matching parameters
		elif isinstance(reference, signature.SignatureParameter):

			# Check if atleast one parameter matches
			if not command or command[0] != reference:
				return not reference.required

			# Gather all matching parameters
			if reference.array:
				matched_parameters[reference.label] = []
				while command and command[0] == reference:
					matched_parameters[reference.label].append(command.pop(0).value)

			# Gather first matching parameter
			else:
				matched_parameters[reference.label] = command.pop(0).value

			return True

		# Matching flags
		elif isinstance(reference, signature.SignatureFlag):

			# Check if there are flags left
			if not command:
				return not reference.required

			# Check if flag matches
			if reference in command:
				matched_flags.append(reference.label)
				command.remove(reference)
				return True

			return not reference.required

		elif isinstance(reference, signature.SignatureVariable):

			# Check if there are variables left
			if not command:
				return not reference.required

			# Check if variable matches
			for token in command:
				if token == reference:
					matched_variables[token.label] = token.value
					command.remove(token)
					return True

			return not reference.required

	matched = internal(signature)
	for token in command:
		if isinstance(token, command.CommandParameter):
			unmatched_parameters.append(token.value)
		elif isinstance(token, command.CommandFlag):
			unmatched_flags.append(token.label)
		elif isinstance(token, command.CommandVariable):
			unmatched_variables[token.label] = token.value

	return MatchResult(matched, matched_parameters, matched_flags, matched_variables, unmatched_parameters, unmatched_flags, unmatched_variables)
