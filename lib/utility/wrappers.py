
# Native libraries
import re as regex
from os import getenv

# External libraries
import dotenv
from discord.ext import commands

# Local libraries
from . import errors, ui
from lib import parsing


# ---------------------> Environment setup


dotenv.load_dotenv()


# ---------------------> Wrappers


def regex_command(usage: str, param_filter: str = r'([^ ]+)', thesaurus: dict[str, str] = {}):
	# Wraps around commands to split args into flags, params and variables using regex
	#   - incoming func MUST follow async (self, ctx, dialog, summary, params, flags, vars) -> Any
	#   - outgoing func follows async (self, ctx, *, raw: str = '', **args) -> Any
	#   - decorator MUST be placed below @bot.command() decorator

	def decorator(func):
		if hasattr(func, 'signature_command'):
			raise errors.WrapperError('Signature commands and regex commands are mutually exclusive')
		if hasattr(func, 'regex_command'):
			raise errors.WrapperError('Method is already a regex command')

		async def wrapped(self, ctx: commands.Context, *, raw: str = '', **_) -> None:
			SHORT_VAR_FILTER = r'-- ?([^ ]+) ?= ?([^ ]+)'
			LONG_VAR_FILTER = r'-- ?([^ ]+) ?= ?["“](.+)["“]'
			FLAG_FILTER = r'-- ?([^ ]+)'

			flags, vars, params = [], {}, []
			dialog = ui.Dialog(ctx)
			summary = ui.Summary(ctx)
			summary.set_header(f'Resolved {ctx.command.name} command')
			summary.set_field('Usage', f'Given commands are expected to follow the following signature `{ctx.prefix}{ctx.command.name} {usage}`\nUse `{ctx.prefix}help {ctx.command.name}` for more information.')


			# Filter out vars
			raw_vars = regex.findall(LONG_VAR_FILTER, raw)
			raw = regex.sub(LONG_VAR_FILTER, '', raw)
			raw_vars.extend(regex.findall(SHORT_VAR_FILTER, raw))
			raw = regex.sub(SHORT_VAR_FILTER, '', raw)

			for var in raw_vars:
				key, value = var
				if key in thesaurus:
					key = thesaurus[key]
				vars[key] = value

			# Filter out flags
			raw_flags = regex.findall(FLAG_FILTER, raw)
			raw = regex.sub(FLAG_FILTER, '', raw)

			for flag in raw_flags:
				if flag in thesaurus:
					flag = thesaurus[flag]
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

		wrapped.default_command = True
		return wrapped
	return decorator

def signature_command(usage: str = '', thesaurus: dict[str, str] = {}):
	# Wraps around commands to match args to a signature, catches illegal commands and irrelevant arguments
	#   - incoming func MUST follow async (self, ctx, dialog, summary, params, flags, vars) -> Any
	#   - outgoing func follows async (self, ctx, *, raw: str = '', **args) -> Any
	#   - decorator MUST be placed below @bot.command() decorator

	signature = parsing.Signature(usage, {}) # TODO import signature dictionary from settings

	def decorator(func):
		if hasattr(func, 'signature_command'):
			raise parsing.errors.WrapperError('Method is already a signature command')
		if hasattr(func, 'regex_command'):
			raise parsing.errors.WrapperError('Signature commands and regex commands are mutually exclusive')

		async def wrapped(self, ctx: commands.Context, *, raw: str = '', **_) -> None:
			dialog = ui.Dialog(ctx)
			summary = ui.Summary(ctx)
			summary.set_header(f'Resolved {ctx.command.name} command')
			summary.set_field('Usage', f'Given commands are expected to follow the following signature `{ctx.prefix}{ctx.command.name}{" " if usage else ""}{usage}`\nUse `{ctx.prefix}help {ctx.command.name}` for more information.')

			try: # Parse command
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
					if isinstance(err, parsing.errors.UnexpectedTokenError):
						summary.set_field('Unexpected token', f'Found unexpected token `{err.token.raw}`, in given command `{ctx.prefix}{ctx.command.name} {command.raw}`.')
					elif isinstance(err, parsing.errors.UnexpectedEOFError):
						summary.set_field('Unexpected EOF', f'Given command `{command.raw}` has floating operators.')
					else:
						raise err

				# Give feedback
				await dialog.add(embed=summary.make_embed())
				await dialog.cleanup()
				ui.history.add(summary)

				return

			# Match to signature
			result = signature.match(command)
			if not result.matched:
				summary.set_header('Invalid command')
				summary.set_field('Invalid command', f'Given command `{ctx.prefix}{ctx.command.name}{" " if command.raw else ""}{command.raw}` does not match the signature `{ctx.prefix}{ctx.command.name}{" " if signature.raw else ""}{signature.raw}`.')

				# Give feedback
				await dialog.add(embed=summary.make_embed())
				await dialog.cleanup()
				ui.history.add(summary)

				return

			# Warn about unmatched parameters, flags and variables
			if result.unmatched_parameters:
				summary.set_field('Irrellevant parameters', f'Given command `{ctx.prefix}{ctx.command.name} {command.raw}` contains irrellevant parameters: `{", ".join(result.unmatched_parameters)}`. These parameters will be ignored.')
			if result.unmatched_flags:
				summary.set_field('Irrellevant flags', f'Given command `{ctx.prefix}{ctx.command.name} {command.raw}` contains irrellevant flags: `{", ".join(result.unmatched_flags)}`. These flags will be ignored.')
			if result.unmatched_variables:
				summary.set_field('Irrellevant variables', f'Given command `{ctx.prefix}{ctx.command.name} {command.raw}` contains irrellevant variables: `{", ".join(result.unmatched_variables)}`. These variables will be ignored.')

			# Invoke command
			return_value = await func(self, ctx, dialog, summary, result.matched_parameters, result.matched_flags, result.matched_variables)
			if summary.send_on_return and 'quiet' not in result.matched_flags:
				if 'verbose' in result.matched_flags:
					await dialog.add(embed=summary.make_embed())
				else:
					await dialog.add(summary.header)

			await dialog.cleanup()
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
