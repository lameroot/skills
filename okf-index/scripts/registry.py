"""Handler registry shared by run.py and command modules (avoids import cycles)."""
from __future__ import annotations

import argparse
from typing import Callable

Handler = Callable[[argparse.Namespace, object, object], int]
HANDLERS: dict[tuple[str, str], Handler] = {}


def register(resource: str, action: str) -> Callable[[Handler], Handler]:
    def decorator(fn: Handler) -> Handler:
        HANDLERS[(resource, action)] = fn
        return fn

    return decorator
