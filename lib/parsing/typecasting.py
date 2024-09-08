
# Native libraries
from typing import Any, Tuple, Literal

# Local libraries
from . import errors

# Constants
VALID_TYPES = ['any', 'any-array', 'int', 'int-array', 'float', 'float-array', 'str', 'str-array', 'bool', 'bool-array', 'long-string']


# ---------------------> Functions


def cast(raw: Any) -> Tuple[Any, Literal['str', 'int', 'float', 'bool']]:
	"""Casts a raw value to a native type."""

	raw = str(raw)

	try:
		if '.' in raw:
			return float(raw), 'float'
		else:
			return int(raw), 'int'

	except ValueError:
		if raw.lower() == 'true':
			return True, 'bool'
		elif raw.lower() == 'false':
			return False, 'bool'
		else:
			return raw, 'str'

def parse(raw: str) -> Tuple[Literal['any', 'str', 'int', 'float', 'bool'], bool, bool]:
	"""Parses a raw type and returns the type, if it is an array, and if it is a long string."""

	if raw in VALID_TYPES:
		if raw == 'long-string':
			return 'str', False, True
		return raw.replace('-array', ''), '-array' in raw, False
	raise errors.UnknownTypeError(raw)
