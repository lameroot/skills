"""OKF bundle conformance validator (SPEC §9) + `bundle validate` command.

Conformance: every non-reserved .md has parseable frontmatter with a non-empty `type`;
reserved filenames (index.md, log.md) are exempt. Collects ALL violations; never raises.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from envelope import emit_success
from okf.frontmatter import parse as fm_parse
from registry import register

RESERVED = {"index.md", "log.md"}


def validate_bundle(root: str | Path) -> dict:
    root = Path(root)
    violations: list[dict] = []
    if not root.exists():
        return {
            "conformant": False,
            "violations": [{"path": str(root), "rule": "missing", "message": "bundle directory not found"}],
        }
    for path in sorted(root.rglob("*.md")):
        rel = str(path.relative_to(root))
        if path.name in RESERVED:
            continue  # SPEC §3.1 reserved filenames are exempt from concept rules
        try:
            text = path.read_text(encoding="utf-8")
        except Exception as exc:  # noqa: BLE001
            violations.append({"path": rel, "rule": "unreadable", "message": str(exc)})
            continue
        meta, _body = fm_parse(text)
        if not meta:
            violations.append(
                {"path": rel, "rule": "frontmatter", "message": "missing or unparseable YAML frontmatter"}
            )
            continue
        t = meta.get("type")
        if not t or not str(t).strip():
            violations.append({"path": rel, "rule": "type", "message": "missing or empty required 'type'"})
    return {"conformant": not violations, "violations": violations}


@register("bundle", "validate")
def bundle_validate_cmd(args: argparse.Namespace, out, err) -> int:
    result = validate_bundle(args.bundle)
    emit_success(result, out)
    return 0 if result["conformant"] else 1
