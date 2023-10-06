
# Stdlib imports
import re as regex
from glob import iglob
from os.path import join
from typing import Generator


# ---------------------> External Functions


def yield_extensions(sys_path: str = 'extensions', prefix_path: bool = False, recursive: bool = True) -> Generator[str, None, None]:
    # Yields all extension files in path.
    #   - sys_path contains path to extensions                  default is 'extensions'
    #   - prefix_path toggles prefixing with extension path     default is False
    #   - recursive toggles recursive search                    default is True
    
    sys_path = join(sys_path, '**/*.py' if recursive else '*.py')      # Build path dependent on requirements
    for file in iglob(sys_path, recursive=recursive):                  # Use iglob to match all python files
        components = regex.findall(r'\w+', file)[:-1]                  # Split into components and trim extension
        yield '.'.join(components) if prefix_path else components[-1]  # Either return import path or extension name

def extension_path(extension: str, sys_path: str = 'extensions', recursive: bool = True) -> str:
    # Finds extension in sys path, returns full extension path if found
    #   - extension contains extension to search for
    #   - sys_path contains path to extensions                  default is 'extensions'
    #   - recursive toggles recursive search                    default is True

    sys_path = join(sys_path, '**' if recursive else '', f'{extension_name(extension)}.py')  # Build path dependent on requirement
    for file in iglob(sys_path, recursive=recursive):                                        # Use iglob to match all python files
        components = regex.findall(r'\w+', file)[:-1]                                        # Split into components and trim extension
        return '.'.join(components)                                                          # Return full extension path
    return extension                                                                         # If not found return extension

def extension_name(extension_path: str) -> str:
    # Returns extension name from extension path
    #   - extension_path contains path to extension with `.` seperation

    return extension_path.split('.')[-1]
