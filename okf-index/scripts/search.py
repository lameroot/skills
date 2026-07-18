"""search, tag, and bundle stats commands (FTS5 index consumer)."""
from __future__ import annotations

import argparse

from envelope import emit_error, emit_success
from indexer import open_db
from registry import register
from vault import resolve_vault


def _escape(q: str) -> str:
    # Wrap in double-quotes to make FTS5 treat it as a phrase.
    return '"' + q.replace('"', '""') + '"'


@register("search", "search")
def search_cmd(args: argparse.Namespace, out, err) -> int:
    if not getattr(args, "q", "").strip():
        emit_error("usage", "search requires a query string", err)
        return 2

    vault = resolve_vault(create=False)
    db = open_db(vault)
    q = _escape(args.q)
    where = "concepts_fts MATCH ?"
    params: list = [q]
    if getattr(args, "tag", ""):
        where += " AND c.concept_id IN (SELECT concept_id FROM tags WHERE tag=?)"
        params.append(args.tag)
    if getattr(args, "type", ""):
        where += " AND c.type=?"
        params.append(args.type)
    limit = min(getattr(args, "limit", 20) or 20, 200)
    cur = db.cursor()
    cur.execute(
        f"SELECT c.concept_id, c.type, c.title, c.description "
        f"FROM concepts c JOIN concepts_fts f ON c.concept_id=f.concept_id "
        f"WHERE {where} ORDER BY rank LIMIT ?",
        tuple(params) + (limit,),
    )
    rows = [{"concept_id": r[0], "type": r[1], "title": r[2], "description": r[3]} for r in cur.fetchall()]
    emit_success({"results": rows, "count": len(rows)}, out)
    return 0


@register("tag", "list")
def tag_list_cmd(args: argparse.Namespace, out, err) -> int:
    vault = resolve_vault(create=False)
    db = open_db(vault)
    cur = db.cursor()
    cur.execute("SELECT tag, COUNT(*) as cnt FROM tags GROUP BY tag ORDER BY tag")
    rows = [{"tag": r[0], "count": r[1]} for r in cur.fetchall()]
    emit_success({"tags": rows}, out)
    return 0


@register("tag", "show")
def tag_show_cmd(args: argparse.Namespace, out, err) -> int:
    tag_val = getattr(args, "tag", "").strip()
    if not tag_val:
        emit_error("usage", "tag show requires a tag name", err)
        return 2
    vault = resolve_vault(create=False)
    db = open_db(vault)
    limit = min(getattr(args, "limit", 20) or 20, 200)
    cur = db.cursor()
    cur.execute(
        "SELECT c.concept_id, c.type, c.title FROM concepts c JOIN tags t ON c.concept_id=t.concept_id WHERE t.tag=? ORDER BY c.concept_id LIMIT ?",
        (tag_val, limit),
    )
    rows = [{"concept_id": r[0], "type": r[1], "title": r[2]} for r in cur.fetchall()]
    emit_success({"tag": tag_val, "concepts": rows, "count": len(rows)}, out)
    return 0


@register("bundle", "stats")
def bundle_stats_cmd(args: argparse.Namespace, out, err) -> int:
    vault = resolve_vault(create=False)
    db = open_db(vault)
    cur = db.cursor()
    cur.execute("SELECT type, source, COUNT(*) FROM concepts GROUP BY type, source ORDER BY type, source")
    rows = [{"type": r[0], "source": r[1], "count": r[2]} for r in cur.fetchall()]
    cur.execute("SELECT COUNT(*) FROM concepts")
    total = cur.fetchone()[0]
    emit_success({"total": total, "by_type_and_source": rows}, out)
    return 0
