
# Native libraries
from typing import Any, Tuple, Literal

# Local libraries
from . import errors

# Constants
VALID_TYPES = ['any', 'any-array', 'int', 'int-array', 'float', 'float-array', 'str', 'long-string', 'str-array', 'bool', 'bool-array']


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

def parse(raw: str) -> Tuple[Literal['str', 'int', 'float', 'bool'], bool]:
	"""Parses a raw type and returns the type and if it is an array."""

	if raw in VALID_TYPES:
		if raw == 'long-string':
			return 'any', True
		return raw.replace('-array', ''), '-array' in raw
	raise errors.UnknownTypeError(raw)
