#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "keyring>=25,<26",
#   "pyyaml>=6,<7",
#   "unidecode>=1.3,<2",
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
    from . import doctor  # noqa: F401  registers doctor/check handler
    from . import indexer  # noqa: F401  registers bundle/index handler
    from . import search  # noqa: F401  registers search/tag/stats handlers
    from .connectors import doc as _doc_mod, note as _note_mod  # noqa: F401
    from .okf import validate  # noqa: F401  registers bundle/validate handler
    from .envelope import emit_error, emit_success
    from .errors import SkillError, UsageError
    from .registry import HANDLERS, register
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import auth  # noqa: F401,E402  type: ignore[no-redef]
    import clock  # type: ignore[no-redef]
    import doctor  # noqa: F401,E402  type: ignore[no-redef]
    import indexer  # noqa: F401,E402  type: ignore[no-redef]
    import search  # noqa: F401,E402  type: ignore[no-redef]
    from connectors import doc as _doc_mod, note as _note_mod  # noqa: F401,E402
    from okf import validate  # noqa: F401,E402  type: ignore[no-redef]
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
    for act, help_text in (
        ("status", "show credential sources (never values)"),
        ("setup", "store credentials in the OS keyring"),
        ("check", "report configured/missing credentials"),
        ("delete", "remove credentials from the OS keyring"),
    ):
        p = auth_actions.add_parser(act, help=help_text, formatter_class=_TimedHelpFormatter)
        p.add_argument("--json", action="store_true", help="JSON output")
        if act in ("setup", "delete"):
            p.add_argument("--dry-run", action="store_true", help="preview without writing")
            p.add_argument("--yes", action="store_true", help="execute the mutation")

    doctor_p = resources.add_parser("doctor", help="atomic readiness check", formatter_class=_TimedHelpFormatter)
    doctor_p.set_defaults(action="check")
    doctor_p.add_argument("--json", action="store_true", help="JSON output")

    bundle = resources.add_parser("bundle", help="bundle operations", formatter_class=_TimedHelpFormatter)
    bundle_actions = bundle.add_subparsers(dest="action", required=True, metavar="<action>")
    bv = bundle_actions.add_parser("validate", help="check OKF v0.1 conformance", formatter_class=_TimedHelpFormatter)
    bv.add_argument("--bundle", required=True, help="path to OKF bundle/vault dir")
    bv.add_argument("--json", action="store_true", help="JSON output")
    bi = bundle_actions.add_parser("index", help="(re)build the FTS5 index", formatter_class=_TimedHelpFormatter)
    bi.add_argument("--rebuild", action="store_true", help="full rebuild (ignore content_hash)")
    bi.add_argument("--json", action="store_true", help="JSON output")
    bi.add_argument("--dry-run", action="store_true", help="preview without writing")
    bi.add_argument("--yes", action="store_true", help="execute the mutation")
    bs = bundle_actions.add_parser("stats", help="bundle concept counts by type/source", formatter_class=_TimedHelpFormatter)
    bs.add_argument("--json", action="store_true", help="JSON output")

    srch = resources.add_parser("search", help="search the knowledge base", formatter_class=_TimedHelpFormatter)
    srch.set_defaults(action="search")
    srch.add_argument("q", help="search query (FTS5 MATCH)")
    srch.add_argument("--tag", help="filter by tag")
    srch.add_argument("--type", help="filter by OKF type")
    srch.add_argument("--limit", type=int, default=20, help="max results (default 20)")
    srch.add_argument("--json", action="store_true", help="JSON output")

    tag = resources.add_parser("tag", help="tag index", formatter_class=_TimedHelpFormatter)
    tag_actions = tag.add_subparsers(dest="action", required=True, metavar="<action>")
    tag_list = tag_actions.add_parser("list", help="list all tags with counts", formatter_class=_TimedHelpFormatter)
    tag_list.add_argument("--json", action="store_true", help="JSON output")
    tag_show = tag_actions.add_parser("show", help="concepts for a specific tag", formatter_class=_TimedHelpFormatter)
    tag_show.add_argument("tag", help="tag name")
    tag_show.add_argument("--limit", type=int, default=20, help="max results")
    tag_show.add_argument("--json", action="store_true", help="JSON output")

    note_p = resources.add_parser("note", help="personal notes", formatter_class=_TimedHelpFormatter)
    note_actions = note_p.add_subparsers(dest="action", required=True, metavar="<action>")
    note_add = note_actions.add_parser("add", help="add a note as an OKF Note concept", formatter_class=_TimedHelpFormatter)
    note_add.add_argument("text", nargs="?", default="", help="note text (or use --file)")
    note_add.add_argument("--file", help="read note body from a file")
    note_add.add_argument("--title", help="concept title (default: first line)")
    note_add.add_argument("--json", action="store_true", help="JSON output")
    note_add.add_argument("--dry-run", action="store_true", help="preview without writing")
    note_add.add_argument("--yes", action="store_true", help="execute the mutation")

    doc_p = resources.add_parser("doc", help="local documents", formatter_class=_TimedHelpFormatter)
    doc_actions = doc_p.add_subparsers(dest="action", required=True, metavar="<action>")
    doc_ingest_p = doc_actions.add_parser("ingest", help="ingest .md/.txt as Document concepts", formatter_class=_TimedHelpFormatter)
    doc_ingest_p.add_argument("path", help="file or directory")
    doc_ingest_p.add_argument("--recursive", action="store_true", help="recurse into directories")
    doc_ingest_p.add_argument("--json", action="store_true", help="JSON output")
    doc_ingest_p.add_argument("--dry-run", action="store_true", help="preview without writing")
    doc_ingest_p.add_argument("--yes", action="store_true", help="execute the mutation")

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
