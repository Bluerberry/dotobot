
# Wraps around commands to split args into flags and params.
#  - func MUST follow async (self, ctx, flags, params) -> Any
#  - decorator should be placed below @bot.command() decorator

def extract_flags():
    def wrapper(func):
        async def wrapped(self, ctx, *args, **kwargs):
            flags  = []
            params = []

            for arg in list(args):
                if arg.startswith('--'):
                    flags.append(arg[2:])
                else:
                    params.append(arg)

            return await func(self, ctx, flags, params)
        return wrapped
    return wrapper

# Yields all extension files in path.
#  - import_path prefixes extension with import path
#  - recursive goes deeper than one directory

from glob import iglob
from os.path import join
import re as regex

def yield_extensions(path, import_path = False, recursive = True):
    path = join(path, '.\\**\\*.py' if recursive else '.\\*.py')        # Build path dependent on requirements
    for file in iglob(path, recursive = True):                          # Use iglob to match all python files
        components = regex.findall(r'\w+', file[:-3])                   # Split into components and trim extension
        yield '.'.join(components) if import_path else components[-1]   # Either return composit or last component