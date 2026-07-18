"""SQLite FTS5 index over the OKF vault. WAL, incremental (content_hash), idempotent."""
from __future__ import annotations

import argparse
import sqlite3
import time as _time
from datetime import datetime, timezone
from pathlib import Path

from connectors import is_confirmed, is_dry_run
from envelope import emit_error, emit_success
from okf.concept import content_hash
from okf.frontmatter import parse as fm_parse
from registry import register
from vault import resolve_vault

DB_NAME = ".okf/index.db"
RESERVED = {"index.md", "log.md"}
TOKENIZER = "unicode61 remove_diacritics 2"


def open_db(vault: Path) -> sqlite3.Connection:
    db_path = vault / DB_NAME
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    cur = conn.cursor()
    cur.execute(
        "CREATE TABLE IF NOT EXISTS concepts("
        "concept_id TEXT PRIMARY KEY, type TEXT, title TEXT, description TEXT, "
        "resource TEXT, source TEXT, source_id TEXT, content_hash TEXT, mtime TEXT)"
    )
    cur.execute(
        f"CREATE VIRTUAL TABLE IF NOT EXISTS concepts_fts USING fts5("
        f"concept_id UNINDEXED, title, description, body, tags, "
        f"tokenize='{TOKENIZER}')"
    )
    cur.execute(
        "CREATE TABLE IF NOT EXISTS tags(tag TEXT, concept_id TEXT, PRIMARY KEY(tag, concept_id))"
    )
    return conn


def walk_concepts(vault: Path):
    for path in sorted(vault.rglob("*.md")):
        if path.name in RESERVED:
            continue
        rel = str(path.relative_to(vault))
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue
        meta, body = fm_parse(text)
        if not meta or not meta.get("type"):
            continue
        mtime = path.stat().st_mtime
        yield rel, meta, body, mtime


def index_bundle(vault: Path, rebuild: bool = False) -> dict:
    db = open_db(vault)
    cur = db.cursor()
    indexed = updated = skipped = 0
    for rel, meta, body, mtime in walk_concepts(vault):
        concept_id = rel
        ch = meta.get("content_hash") or content_hash(body)
        title = meta.get("title", "") or path.stem
        desc = meta.get("description", "")
        type_ = meta.get("type", "")
        resource = meta.get("resource", "")
        source = meta.get("source", "")
        source_id = meta.get("source_id", "")
        tags_list = meta.get("tags") or []
        mtime_s = datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat()

        if not rebuild:
            cur.execute("SELECT content_hash FROM concepts WHERE concept_id=?", (concept_id,))
            row = cur.fetchone()
            if row and row[0] == ch:
                skipped += 1
                continue
            is_update = row is not None
        else:
            is_update = False

        cur.execute("DELETE FROM concepts_fts WHERE concept_id=?", (concept_id,))
        cur.execute("DELETE FROM tags WHERE concept_id=?", (concept_id,))
        cur.execute(
            "INSERT OR REPLACE INTO concepts VALUES(?,?,?,?,?,?,?,?,?)",
            (concept_id, type_, title, desc, resource, source, source_id, ch, mtime_s),
        )
        for t in tags_list:
            cur.execute("INSERT OR IGNORE INTO tags VALUES(?,?)", (t, concept_id))
        body_fragment = (body or "")[:50000]  # bounded body for FTS
        cur.execute(
            "INSERT INTO concepts_fts(concept_id, title, description, body, tags) VALUES(?,?,?,?,?)",
            (concept_id, title, desc, body_fragment, " ".join(tags_list)),
        )
        if is_update:
            updated += 1
        else:
            indexed += 1
    db.commit()
    return {"indexed": indexed, "updated": updated, "skipped": skipped}


@register("bundle", "index")
def bundle_index_cmd(args: argparse.Namespace, out, err) -> int:
    vault = resolve_vault(create=not is_dry_run(args))
    if is_dry_run(args):
        emit_success({"dry_run": True, "target": str(vault)}, out)
        return 0
    if not is_confirmed(args):
        emit_error("usage", "bundle index requires --dry-run or --yes", err, hint="set OKF_INDEX_AUTO_CONFIRM=1 for automation")
        return 2
    result = index_bundle(vault, rebuild=getattr(args, "rebuild", False))
    emit_success(result, out)
    return 0
