"""note resource: add a personal note as an OKF Note concept."""
from __future__ import annotations

import argparse
from pathlib import Path

from connectors import is_confirmed, is_dry_run
from enrich import enrich, first_line
from envelope import emit_error, emit_success
from errors import UsageError
from okf.concept import Concept
from okf.writer import write_concept
from registry import register
from vault import resolve_vault


@register("note", "add")
def note_add(args: argparse.Namespace, out, err) -> int:
    body = args.text or ""
    if args.file:
        body = Path(args.file).read_text(encoding="utf-8", errors="replace")
    if not body.strip():
        raise UsageError("note body is empty", code="empty_note", hint="provide text or --file")
    title = args.title or first_line(body) or "untitled"
    concept = Concept(type="Note", title=title, body=body, source="note", resource=args.file or "")
    enrich(concept)
    vault = resolve_vault(create=not is_dry_run(args))

    if is_dry_run(args):
        emit_success({"dry_run": True, "target": {"type": "Note", "title": title}}, out)
        return 0
    if not is_confirmed(args):
        emit_error("usage", "note add requires --dry-run or --yes", err, hint="set OKF_INDEX_AUTO_CONFIRM=1 for automation")
        return 2
    path = write_concept(vault, concept)
    emit_success({"created": {"path": str(path.relative_to(vault)), "type": "Note", "title": title}}, out)
    return 0
