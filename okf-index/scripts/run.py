#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "keyring>=25,<26",
# ]
# ///
"""okf-index CLI launcher.

Run from the skill directory:
  uv run --script scripts/run.py schema get --json
  uv run --script scripts/run.py auth status --json
  uv run --script scripts/run.py schema get --help
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:  # package-style import when loaded as a module; fallback for direct script run
    from . import auth  # noqa: F401  registers auth/* handlers
    from . import clock
    from .envelope import emit_error, emit_success
    from .errors import SkillError, UsageError
    from .registry import HANDLERS, register
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import auth  # noqa: F401,E402  type: ignore[no-redef]
    import clock  # type: ignore[no-redef]
    from envelope import emit_error, emit_success  # type: ignore[no-redef]
    from errors import SkillError, UsageError  # type: ignore[no-redef]
    from registry import HANDLERS, register  # type: ignore[no-redef]

VERSION = "0.1.0"
OKF_VERSION = "0.1"


class _TimedHelpFormatter(argparse.RawDescriptionHelpFormatter):
    """Prepend the AGENTS.md-mandated `Current time (...)` line to every --help level."""

    def format_help(self) -> str:
        try:
            header = clock.time_line() + "\n\n"
        except Exception:  # noqa: BLE001 - never let help crash on clock failure
            header = ""
        return header + super().format_help()


def build_schema() -> dict:
    grouped: dict[str, dict] = {}
    for resource, action in sorted(HANDLERS):
        grouped.setdefault(resource, {"resource": resource, "actions": []})["actions"].append(action)
    return {
        "skill": "okf-index",
        "version": VERSION,
        "okf_version": OKF_VERSION,
        "commands": list(grouped.values()),
    }


@register("schema", "get")
def schema_get(args: argparse.Namespace, out, err) -> int:
    emit_success(build_schema(), out)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run.py",
        description="okf-index — OKF knowledge base builder (Confluence/web/docs/notes -> Obsidian vault + FTS5 search).",
        formatter_class=_TimedHelpFormatter,
    )
    resources = parser.add_subparsers(dest="resource", required=True, metavar="<resource>")

    schema = resources.add_parser("schema", help="CLI schema introspection", formatter_class=_TimedHelpFormatter)
    schema_actions = schema.add_subparsers(dest="action", required=True, metavar="<action>")
    schema_get = schema_actions.add_parser(
        "get", help="print the machine-readable command schema", formatter_class=_TimedHelpFormatter
    )
    schema_get.add_argument("--json", action="store_true", help="JSON output (schema get is JSON by default)")

    auth = resources.add_parser("auth", help="credentials lifecycle", formatter_class=_TimedHelpFormatter)
    auth_actions = auth.add_subparsers(dest="action", required=True, metavar="<action>")
    auth_status = auth_actions.add_parser(
        "status", help="show credential sources (never values)", formatter_class=_TimedHelpFormatter
    )
    auth_status.add_argument("--json", action="store_true", help="JSON output")

    return parser


def _execute(args: argparse.Namespace, out=None, err=None) -> int:
    """Dispatch a parsed namespace to its handler; convert SkillError -> structured stderr."""
    out = sys.stdout if out is None else out
    err = sys.stderr if err is None else err
    try:
        key = (getattr(args, "resource", None), getattr(args, "action", None))
        handler = HANDLERS.get(key)
        if handler is None:
            raise UsageError("unknown_command", f"unknown command: {key[0] or ''} {key[1] or ''}".strip())
        return handler(args, out, err)
    except SkillError as exc:
        emit_error(
            exc.code,
            str(exc),
            err,
            hint=exc.hint,
            retriable=exc.retriable,
            exit_code=exc.exit_code,
        )
        return exc.exit_code


def main(argv=None, out=None, err=None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        # argparse already wrote diagnostics to stderr; preserve its exit code (2 for usage).
        return exc.code if isinstance(exc.code, int) else 2
    return _execute(args, out, err)


if __name__ == "__main__":
    sys.exit(main())
