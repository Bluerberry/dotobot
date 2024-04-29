
# Native libraries
import re as regex
from os import getenv
from copy import deepcopy

# External libraries
import dotenv
from discord.ext import commands

# Local libraries
from . import errors, ui
from lib import parsing

# Constants
SHORT_VAR_FILTER = r'-- ?([^ ]+) ?= ?([^ ]+)'
LONG_VAR_FILTER = r'-- ?([^ ]+) ?= ?["“](.+)["“]'
FLAG_FILTER = r'-- ?([^ ]+)'
DEFAULT_COMMAND_THESAURUS = {
	'quiet': ['q'],
	'verbose': ['v'],
}


# ---------------------> Environment setup


dotenv.load_dotenv()


# ---------------------> Wrappers


def regex_command(param_filter: str = r'([^ ]+)', thesaurus: dict[str, list[str]] = {}):
	# Wraps around commands to split args into flags, params and variables using regex
	#   - incoming func MUST follow async (self, ctx, dialog, summary, params, flags, vars) -> Any
	#   - outgoing func follows async (self, ctx, *, raw: str = '', **args) -> Any
	#   - decorator MUST be placed below @bot.command() decorator

	temp = deepcopy(DEFAULT_COMMAND_THESAURUS)
	temp.update(thesaurus)
	thesaurus = temp

	def decorator(func):
		if hasattr(func, 'signature_command'):
			raise errors.WrapperError('Signature commands and regex commands are mutually exclusive')
		if hasattr(func, 'regex_command'):
			raise errors.WrapperError('Method is already a regex command')

		async def wrapped(self, ctx: commands.Context, *, raw: str = '', **_) -> None:
			params, flags, vars = [], [], {}
			dialog = ui.Dialog(ctx)
			summary = ui.Summary(ctx)
			summary.set_header(f'Resolved {ctx.command.name} command')

			# Filter out vars
			raw_vars = regex.findall(LONG_VAR_FILTER, raw)
			raw = regex.sub(LONG_VAR_FILTER, '', raw)
			raw_vars.extend(regex.findall(SHORT_VAR_FILTER, raw))
			raw = regex.sub(SHORT_VAR_FILTER, '', raw)

			for raw_var in raw_vars:
				raw_key, raw_value = raw_var
				for key, synonyms in thesaurus.items():
					if raw_key in synonyms:
						raw_key = key
						break
				
				vars[raw_key] = raw_value

			# Filter out flags
			raw_flags = regex.findall(FLAG_FILTER, raw)
			raw = regex.sub(FLAG_FILTER, '', raw)

			for flag in raw_flags:
				for key, synonyms in thesaurus.items():
					if flag in synonyms:
						flag = key
						break
				
				flags.append(flag)

			# Filter out parameters
			params = regex.findall(param_filter, raw)

			# Invoke command
			return_value = await func(self, ctx, dialog, summary, params, flags, vars)
			if summary.send_on_return and 'quiet' not in flags:
				if 'verbose' in flags:
					await dialog.add(embed=summary.make_embed())
				else:
					await dialog.add(summary.header)

			await dialog.cleanup()
			ui.history.add(summary)
			return return_value
		
		wrapped.regex_command = True
		return wrapped
	return decorator

def signature_command(usage: str = '', thesaurus: dict[str, list[str]] = {}):
	# Wraps around commands to match args to a signature, catches illegal commands and irrelevant arguments
	#   - incoming func MUST follow async (self, ctx, dialog, summary, params, flags, vars) -> Any
	#   - outgoing func follows async (self, ctx, *, raw: str = '', **args) -> Any
	#   - decorator MUST be placed below @bot.command() decorator

	signature = parsing.Signature(usage) # TODO import signature dictionary from settings
	temp = deepcopy(DEFAULT_COMMAND_THESAURUS)
	temp.update(thesaurus)
	thesaurus = temp

	def decorator(func):
		if hasattr(func, 'signature_command'):
			raise parsing.errors.WrapperError('Method is already a signature command')
		if hasattr(func, 'regex_command'):
			raise parsing.errors.WrapperError('Signature commands and regex commands are mutually exclusive')

		async def wrapped(self, ctx: commands.Context, *, raw: str = '', **_) -> None:
			dialog = ui.Dialog(ctx)
			summary = ui.Summary(ctx)
			summary.set_header(f'Resolved {ctx.command.name} command')

			# Parse command
			try:
				command = parsing.Command(raw, {}, thesaurus) # TODO import command dictionary from settings
			except Exception as err:
				if isinstance(err, parsing.errors.UnknownObjectError):
					summary.set_header('Internal error')
					summary.set_field('Unknown Object', f'Congratulations, you found a massive internal issue! Please report this to the developers, thanks babygirl <3.')

				elif isinstance(err, parsing.errors.UnknownOperatorError):
					summary.set_header('Internal error')
					summary.set_field('Unknown Operator', f'Your command contains the unknown operator `{err.args}`. This is either your fault, or a massive internal issue! Please report this to the developers, thanks babygirl <3.')

				else:
					summary.set_header('Invalid command')
					if isinstance(err, parsing.errors.ExpectedTokenError):
						summary.set_field('Expected Token', f'Given command `{ctx.prefix}{ctx.command.name}{" " + raw if raw else ""}` is missing a token.')
					elif isinstance(err, parsing.errors.UnexpectedOperatorError):
						summary.set_field('Unexpected Operator', f'Given command `{ctx.prefix}{ctx.command.name}{" " + raw if raw else ""}` contains an unexpected operator.')
					elif isinstance(err, parsing.errors.ExpectedOperatorError):
						summary.set_field('Expected Operator', f'Given command `{ctx.prefix}{ctx.command.name}{" " + raw if raw else ""}` is missing an expected operator.')
					else:
						summary.set_field('Unknown Error', f'Given command `{ctx.prefix}{ctx.command.name}{" " + raw if raw else ""}` contains an unknown error.')			

				# Give feedback
				summary.set_field('Usage', f'Given commands are expected to follow the following signature `{ctx.prefix}{ctx.command.name}{" " + signature.raw if signature.raw else ""}`.\nUse `{ctx.prefix}help {ctx.command.name}` for more information.')
				await dialog.add(embed=summary.make_embed())
				await dialog.cleanup()
				ui.history.add(summary)

				return

			# Match to signature
			try:
				matched, unmatched = signature.match(command)
			except Exception as err:
				if isinstance(err, parsing.errors.UnknownObjectError):
					summary.set_header('Internal error')
					summary.set_field('Unknown Object', f'Congratulations, you found a massive internal issue! Please report this to the developers, thanks babygirl <3.')
				else:
					summary.set_header('Invalid command')
					if isinstance(err, parsing.errors.NoMatchError):
						summary.set_field('No Matches', f'Given command `{ctx.prefix}{ctx.command.name}{" " + command.raw if command.raw else ""}` does not match the signature.')
					elif isinstance(err, parsing.errors.TooManyMatchesError):
						summary.set_field('Too Many Matches', f'Given command `{ctx.prefix}{ctx.command.name}{" " + command.raw if command.raw else ""}` matches the signature multiple times.')
					else:
						print(err)
						summary.set_field('Unknown Error', f'Given command `{ctx.prefix}{ctx.command.name}{" " + command.raw if command.raw else ""}` contains an unknown error.')

				# Give feedback
				summary.set_field('Usage', f'Given commands are expected to follow the following signature `{ctx.prefix}{ctx.command.name}{" " + signature.raw if signature.raw else ""}`.\nUse `{ctx.prefix}help {ctx.command.name}` for more information.')
				await dialog.add(embed=summary.make_embed())
				await dialog.cleanup()
				ui.history.add(summary)

				return

			# Warn about unmatched parameters, flags and variables
			if unmatched.parameters:
				summary.set_field('Irrellevant parameters', f'Given command `{ctx.prefix}{ctx.command.name} {command.raw}` contains irrellevant parameters: `{", ".join(unmatched.parameters)}`. These parameters will be ignored.')
			if unmatched.flags:
				summary.set_field('Irrellevant flags', f'Given command `{ctx.prefix}{ctx.command.name} {command.raw}` contains irrellevant flags: `{", ".join(unmatched.flags)}`. These flags will be ignored.')
			if unmatched.variables:
				summary.set_field('Irrellevant variables', f'Given command `{ctx.prefix}{ctx.command.name} {command.raw}` contains irrellevant variables: `{", ".join(unmatched.variables)}`. These variables will be ignored.')
			if unmatched.parameters or unmatched.flags or unmatched.variables:
				summary.set_field('Usage', f'Given commands are expected to follow the following signature `{ctx.prefix}{ctx.command.name}{" " + signature.raw if signature.raw else ""}`.\nUse `{ctx.prefix}help {ctx.command.name}` for more information.')

			# Invoke command
			return_value = await func(self, ctx, dialog, summary, matched.parameters, matched.flags, matched.variables)

			await dialog.cleanup()
			if summary.send_on_return and 'quiet' not in matched.flags:
				if 'verbose' in matched.flags:
					await dialog.add(embed=summary.make_embed())
				else:
					await dialog.add(summary.header)

			ui.history.add(summary)
			return return_value
		
		wrapped.signature_command = True
		return wrapped
	return decorator

def dev_only():
	# Wraps around commands to make it dev only
	#   - incoming func signature does not matter
	#   - outgoing func signature does not change
	#   - decorator MUST be placed below @bot.command() decorator

	def predicate(ctx: commands.Context):
		return str(ctx.author.id) in getenv('DEVELOPER_IDS')
	return commands.check(predicate)
