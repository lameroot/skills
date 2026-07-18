"""OKF log.md generator/appender (SPEC §7). ISO date sections, newest first."""
from __future__ import annotations

import re
from pathlib import Path

_DATE_RE = re.compile(r"^## (\d{4}-\d{2}-\d{2})")


def format_log(entries: dict[str, list[str]]) -> str:
    lines = ["# Directory Update Log"]
    for date in sorted(entries, reverse=True):
        lines += ["", f"## {date}"]
        for e in entries[date]:
            lines.append(f"* {e}")
    return "\n".join(lines) + "\n"


def parse_log(text: str) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    cur: str | None = None
    for line in text.splitlines():
        m = _DATE_RE.match(line)
        if m:
            cur = m.group(1)
            out.setdefault(cur, [])
        elif line.startswith("* ") and cur:
            out[cur].append(line[2:])
    return out


def append_log(log_path: str | Path, date_iso: str, new_entries: list[str]) -> None:
    p = Path(log_path)
    existing: dict[str, list[str]] = {}
    if p.exists():
        existing = parse_log(p.read_text(encoding="utf-8"))
    bucket = existing.setdefault(date_iso, [])
    for e in new_entries:
        if e not in bucket:
            bucket.append(e)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(format_log(existing), encoding="utf-8")
