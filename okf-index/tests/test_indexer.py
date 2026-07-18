"""SCIU 11 tests: FTS5 indexer (WAL, incremental, idempotent)."""
import sqlite3

import run
import vault
from indexer import index_bundle, open_db, walk_concepts
from okf.frontmatter import dump as fm_dump


def _vault(monkeypatch, tmp_path):
    v = tmp_path / "vault"
    monkeypatch.setenv("OKF_VAULT_PATH", str(v))
    return v


def _write_concept(vault, source, slug, meta, body=""):
    d = vault / source
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{slug}.md"
    p.write_text(fm_dump(meta, body), encoding="utf-8")
    return str(p.relative_to(vault))


def test_index_builds_fts5_and_wal(monkeypatch, tmp_path):
    v = _vault(monkeypatch, tmp_path)
    _write_concept(v, "doc", "a", {"type": "Document", "title": "Alpha", "tags": ["test"]}, "alpha body")
    vault.resolve_vault(path=v, skill_root=tmp_path / "skill")  # ensures vault exists
    result = index_bundle(v)
    assert result["indexed"] == 1
    db = open_db(v)
    assert db.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    # FTS searchable
    rows = db.execute("SELECT concept_id FROM concepts_fts WHERE concepts_fts MATCH 'alpha'").fetchall()
    assert len(rows) == 1
    # tag in tags table
    rows = db.execute("SELECT tag FROM tags WHERE concept_id=?", ("doc/a.md",)).fetchall()
    assert rows[0][0] == "test"


def test_reingest_same_hash_no_dup(monkeypatch, tmp_path):
    v = _vault(monkeypatch, tmp_path)
    _write_concept(v, "doc", "b", {"type": "Doc", "title": "B"}, "body")
    vault.resolve_vault(path=v, skill_root=tmp_path / "skill")
    r1 = index_bundle(v)
    assert r1["indexed"] == 1
    r2 = index_bundle(v)
    assert r2["indexed"] == 0 and r2["skipped"] == 1 and r2["updated"] == 0


def test_since_updates_only_changed(monkeypatch, tmp_path):
    v = _vault(monkeypatch, tmp_path)
    _write_concept(v, "doc", "a", {"type": "Doc", "title": "A"}, "body a")
    _write_concept(v, "doc", "b", {"type": "Doc", "title": "B"}, "body b")
    vault.resolve_vault(path=v, skill_root=tmp_path / "skill")
    index_bundle(v)
    # modify only a
    p = v / "doc" / "a.md"
    p.write_text(fm_dump({"type": "Doc", "title": "A modified"}, "changed"), encoding="utf-8")
    # touch mtime (filesystem dependent, just re-index with rebuild=False)
    r = index_bundle(v, rebuild=False)
    assert r["updated"] == 1 and r["skipped"] == 1


def test_bundle_index_cli_works(monkeypatch, tmp_path):
    v = _vault(monkeypatch, tmp_path)
    vault.resolve_vault(path=v, skill_root=tmp_path / "skill")
    _write_concept(v, "doc", "a", {"type": "Doc", "title": "A"}, "body")
    rc = run.main(["bundle", "index", "--yes", "--json"])
    assert rc == 0
