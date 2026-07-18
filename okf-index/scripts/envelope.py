"""JSON envelopes. Success -> stdout; structured error -> stderr. Never mix streams."""
from __future__ import annotations

import json
from typing import Any


def emit_success(data: Any, stream, *, code: int = 0) -> int:
    """Write `{success:true, data}` to `stream` (stdout). Returns the success exit code (0)."""
    json.dump({"success": True, "data": data}, stream, ensure_ascii=False)
    stream.write("\n")
    return code


def emit_error(
    code: str,
    message: str,
    stream,
    *,
    hint: str | None = None,
    retriable: bool = False,
    exit_code: int = 1,
) -> int:
    """Write a structured error `{success:false, error:{...}}` to `stream` (stderr).

    Returns the semantic exit_code so callers can propagate it.
    """
    err: dict[str, Any] = {
        "success": False,
        "error": {"code": code, "message": message, "retriable": retriable},
    }
    if hint is not None:
        err["error"]["hint"] = hint
    json.dump(err, stream, ensure_ascii=False)
    stream.write("\n")
    return exit_code
