"""
Base configuration utilities.
"""
import os
from typing import TypeVar, Optional

T = TypeVar('T')


class ImproperlyConfigured(Exception):
    """Raises when a environment variable is missing."""

    def __init__(self, variable_name: str, *args, **kwargs):
        self.variable_name = variable_name
        self.message = f"Set the {variable_name} environment variable."
        super().__init__(self.message, *args, **kwargs)


def getenv(var_name: str, cast_to: type[T] = str, default: Optional[T] = None) -> T:
    """Gets an environment variable or raises an exception.

    Args:
        var_name: An environment variable name.
        cast_to: A type to cast.
        default: Default value if variable is not set.

    Returns:
        A value of the environment variable.

    Raises:
        ImproperlyConfigured: If the environment variable is missing and no default.
    """
    try:
        value = os.environ[var_name]
        return cast_to(value)
    except KeyError:
        if default is not None:
            return default
        raise ImproperlyConfigured(var_name)
    except ValueError:
        raise ValueError(f"The value {value} can't be cast to {cast_to}.")
