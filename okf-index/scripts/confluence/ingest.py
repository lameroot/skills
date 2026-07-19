"""confluence resource: page get/search + ingest (single or tree) as OKF concepts."""
from __future__ import annotations

import argparse
import re

from confluence.client import get_client, html_to_markdown
from connectors import is_confirmed, is_dry_run
from enrich import enrich
from envelope import emit_error, emit_success
from errors import NotFoundError, PermissionDeniedError, UsageError
from okf.concept import Concept
from okf.writer import list_concepts, write_concept
from registry import register
from vault import resolve_vault

_URL_PAGE_ID_RE = re.compile(r"/pages/(\d+)")
_QS_PAGE_ID_RE = re.compile(r"[?&]pageId=(\d+)")


def parse_page_id(arg: str) -> str:
    """Accept a numeric page ID or a Confluence URL; return the numeric ID."""
    arg = str(arg).strip()
    if arg.isdigit():
        return arg
    m = _URL_PAGE_ID_RE.search(arg) or _QS_PAGE_ID_RE.search(arg)
    if m:
        return m.group(1)
    raise UsageError(f"cannot extract page id from: {arg}", code="bad_page_id")


def _collect_tree(client, page_id: str, depth: int, visited: set | None = None) -> list[tuple[str, dict]]:
    """Recursively collect (page_id, page_data) tuples up to `depth` levels."""
    visited = visited if visited is not None else set()
    if page_id in visited or depth < 0:
        return []
    visited.add(page_id)
    pages: list[tuple[str, dict]] = []
    try:
        page = client.get_page(page_id)
        pages.append((page_id, page))
    except Exception:
        return pages  # skip pages we can't read
    if depth > 0:
        try:
            children = client.get_children(page_id)
            for child in children:
                cid = str(child.get("id", ""))
                if cid:
                    pages.extend(_collect_tree(client, cid, depth - 1, visited))
        except Exception:
            pass  # skip children on error
    return pages


def _page_to_concept(client, page_id: str, page: dict) -> Concept:
    title = page.get("title", page_id)
    html = (page.get("body", {}).get("storage", {}).get("value") or "")
    body = html_to_markdown(html)
    space_key = page.get("space", {}).get("key", "")
    resource = f"{client.base}/spaces/{space_key}/pages/{page_id}"
    concept = Concept(type="ConfluencePage", title=title, body=body, source="confluence", resource=resource)
    concept.source_id = f"confluence-{page_id}"
    return concept


@register("confluence", "ingest")
def confluence_ingest(args: argparse.Namespace, out, err) -> int:
    client = get_client()
    try:
        root_id = parse_page_id(args.page_id)
    except UsageError as exc:
        emit_error(exc.code, str(exc), err, exit_code=2)
        return 2

    depth = getattr(args, "depth", 0) or 0
    vault = resolve_vault(create=not is_dry_run(args))

    # Collect the page tree
    try:
        tree = _collect_tree(client, root_id, depth)
    except PermissionDeniedError:
        emit_error("permission_denied", "Confluence credentials rejected or insufficient", err, exit_code=4)
        return 4
    except Exception as exc:
        emit_error("failure", str(exc), err)
        return 1

    if not tree:
        emit_error("not_found", f"page not found or empty: {root_id}", err, exit_code=3)
        return 3

    if is_dry_run(args):
        emit_success(
            {
                "dry_run": True,
                "root": root_id,
                "depth": depth,
                "would_ingest": [{"id": pid, "title": p.get("title", pid)} for pid, p in tree],
            },
            out,
        )
        return 0
    if not is_confirmed(args):
        emit_error("usage", "confluence ingest requires --dry-run or --yes", err, hint="set OKF_INDEX_AUTO_CONFIRM=1")
        return 2

    title_to_path = list_concepts(vault)
    created = []
    for page_id, page in tree:
        concept = _page_to_concept(client, page_id, page)
        enrich(concept, title_to_path)
        path = write_concept(vault, concept)
        created.append({"path": str(path.relative_to(vault)), "title": concept.title, "id": page_id})

    emit_success({"created": created, "count": len(created)}, out)
    return 0


@register("confluence", "get")
def confluence_get(args: argparse.Namespace, out, err) -> int:
    client = get_client()
    try:
        page_id = parse_page_id(args.page_id)
        page = client.get_page(page_id)
    except NotFoundError:
        emit_error("not_found", f"page not found: {args.page_id}", err, exit_code=3)
        return 3
    except UsageError as exc:
        emit_error(exc.code, str(exc), err, exit_code=2)
        return 2
    title = page.get("title", "")
    html = (page.get("body", {}).get("storage", {}).get("value") or "")
    body = html_to_markdown(html)
    emit_success({"id": page_id, "title": title, "space": page.get("space", {}).get("key", ""), "body": body}, out)
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
