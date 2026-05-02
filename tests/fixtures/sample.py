"""Module docstring (should NOT become a chunk)."""

import os
from typing import Any

CONSTANT = 42


def plain_function(x: int) -> int:
    """Add one to x."""
    return x + 1


def no_docstring(y):
    return y * 2


@staticmethod
def decorated_function(z):
    """Decorated and documented."""
    return z


class Empty:
    """Just a docstring."""


class Greeter:
    """Greets people by name."""

    def __init__(self, prefix: str = "Hello") -> None:
        self.prefix = prefix

    def greet(self, name: str) -> str:
        """Return a greeting."""
        return f"{self.prefix}, {name}!"


@dataclass
class WithDecorator:
    name: str
    age: int = 0


async def async_thing(url: str) -> Any:
    """An async function."""
    return url


if __name__ == "__main__":
    print(plain_function(1))
