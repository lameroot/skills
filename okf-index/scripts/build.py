"""bundle build: declarative ingestion from a sources.yaml manifest."""
from __future__ import annotations

import argparse
from pathlib import Path

import yaml

from connectors import is_confirmed, is_dry_run
from envelope import emit_error, emit_success
from registry import register
from vault import resolve_vault


def _cli_args(resource: str, action: str, **kw) -> argparse.Namespace:
    """Build a synthetic argparse.Namespace for calling handlers directly."""
    ns = argparse.Namespace(resource=resource, action=action, json=True, dry_run=False, yes=False)
    for k, v in kw.items():
        setattr(ns, k, v)
    return ns


@register("bundle", "build")
def bundle_build(args: argparse.Namespace, out, err) -> int:
    path = Path(getattr(args, "from_", "sources.yaml") or "sources.yaml")
    if not path.exists():
        emit_error("not_found", f"manifest not found: {path}", err, exit_code=3)
        return 3
    manifest = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    sources = manifest.get("sources", {})
    if not sources:
        emit_error("usage", "manifest has no 'sources' section", err)
        return 2

    vault = resolve_vault(create=not is_dry_run(args))
    if is_dry_run(args):
        count = sum(len(v) for v in sources.values() if isinstance(v, list))
        emit_success({"dry_run": True, "would_ingest": count, "from": str(path)}, out)
        return 0
    if not is_confirmed(args):
        emit_error("usage", "bundle build requires --dry-run or --yes", err, hint="set OKF_INDEX_AUTO_CONFIRM=1")
        return 2

    from sys import modules
    from importlib import import_module

    results = {"created": []}
    # Ensure handlers are loaded
    for mod_name in ("connectors.note", "connectors.doc", "confluence.ingest", "telegram", "web"):
        try:
            import_module(mod_name)
        except Exception:
            pass

    for kind, entries in sources.items():
        if not isinstance(entries, list):
            continue
        if kind == "confluence":
            h = modules.get("confluence.ingest")
            for entry in entries:
                page_id = str(entry.get("page_id", ""))
                if page_id:
                    ns = _cli_args("confluence", "ingest", page_id=page_id, yes=True)
                    h.confluence_ingest(ns, out, err)
        elif kind == "web":
            h = modules.get("web")
            for entry in entries:
                url = entry.get("url", "")
                if url:
                    ns = _cli_args("web", "fetch", url=url, max_depth=entry.get("max_depth", 1), max_pages=entry.get("max_pages", 10), yes=True)
                    h.web_fetch(ns, out, err) if entry.get("max_depth", 1) <= 1 else h.web_crawl(ns, out, err)
        elif kind == "doc":
            h = modules.get("connectors.doc")
            for entry in entries:
                dp = entry.get("path", "")
                if dp:
                    ns = _cli_args("doc", "ingest", path=dp, recursive=entry.get("recursive", False), yes=True)
                    h.doc_ingest(ns, out, err)
        elif kind == "note":
            h = modules.get("connectors.note")
            for entry in entries:
                text = entry.get("text", "")
                if text:
                    ns = _cli_args("note", "add", text=text, title=entry.get("title", ""), yes=True)
                    h.note_add(ns, out, err)

    emit_success({"status": "done", "from": str(path)}, out)
    return 0
