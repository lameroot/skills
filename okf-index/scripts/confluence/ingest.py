"""confluence resource: page get/search + ingest as OKF concepts."""
from __future__ import annotations

import argparse

from confluence.client import get_client, html_to_markdown
from connectors import is_confirmed, is_dry_run
from enrich import enrich
from envelope import emit_error, emit_success
from errors import NotFoundError, PermissionDeniedError
from okf.concept import Concept
from okf.writer import list_titles, write_concept
from registry import register
from vault import resolve_vault


@register("confluence", "ingest")
def confluence_ingest(args: argparse.Namespace, out, err) -> int:
    client = get_client()
    try:
        page = client.get_page(args.page_id)
    except NotFoundError:
        emit_error("not_found", f"page not found: {args.page_id}", err, exit_code=3)
        return 3
    except PermissionDeniedError:
        emit_error("permission_denied", "Confluence credentials rejected or insufficient", err, exit_code=4)
        return 4
    except Exception as exc:
        emit_error("failure", str(exc), err)
        return 1

    title = page.get("title", args.page_id)
    html = (page.get("body", {}).get("storage", {}).get("value") or "")
    body = html_to_markdown(html)
    resource = f"{client.base}/spaces/{page.get('space',{}).get('key','')}/pages/{args.page_id}"
    concept = Concept(type="ConfluencePage", title=title, body=body, source="confluence", resource=resource)
    concept.source_id = f"confluence-{args.page_id}"

    vault = resolve_vault(create=not is_dry_run(args))
    if is_dry_run(args):
        emit_success({"dry_run": True, "target": {"type": "ConfluencePage", "title": title, "id": args.page_id}}, out)
        return 0
    if not is_confirmed(args):
        emit_error("usage", "confluence ingest requires --dry-run or --yes", err, hint="set OKF_INDEX_AUTO_CONFIRM=1")
        return 2

    enrich(concept, list_titles(vault))
    path = write_concept(vault, concept)
    emit_success({"created": {"path": str(path.relative_to(vault)), "type": "ConfluencePage", "title": title}}, out)
    return 0


@register("confluence", "get")
def confluence_get(args: argparse.Namespace, out, err) -> int:
    client = get_client()
    try:
        page = client.get_page(args.page_id)
    except NotFoundError:
        emit_error("not_found", f"page not found: {args.page_id}", err, exit_code=3)
        return 3
    title = page.get("title", "")
    html = (page.get("body", {}).get("storage", {}).get("value") or "")
    body = html_to_markdown(html)
    emit_success({"id": args.page_id, "title": title, "space": page.get("space", {}).get("key", ""), "body": body}, out)
    return 0


@register("confluence", "search")
def confluence_search(args: argparse.Namespace, out, err) -> int:
    client = get_client()
    cql = f"text ~ '{args.q}'"
    if getattr(args, "space", ""):
        cql += f" AND space = '{args.space}'"
    try:
        results = client.search(cql, limit=min(getattr(args, "limit", 20) or 20, 100))
    except Exception as exc:
        emit_error("failure", str(exc), err)
        return 1
    rows = [{"id": r.get("content", {}).get("id", ""), "title": r.get("title", ""), "url": r.get("url", "")} for r in results]
    emit_success({"results": rows, "count": len(rows)}, out)
    return 0
