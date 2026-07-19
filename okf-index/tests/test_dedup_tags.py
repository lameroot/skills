"""Tests: source_id dedup (no duplicates on re-ingest) + nested Confluence tree."""
import json
from unittest.mock import MagicMock

import confluence.client as cf_client
import enrich
import run
import vault
from confluence.client import ConfluenceClient
from enricher import FakeEnrichProvider
from okf.frontmatter import parse as fm_parse


def _vault(monkeypatch, tmp_path):
    v = tmp_path / "vault"
    monkeypatch.setenv("OKF_VAULT_PATH", str(v))
    return v


def _mock_cf(monkeypatch, **pages):
    fake = MagicMock(spec=ConfluenceClient)
    fake.base = "https://c.example.com"
    def get_page(pid):
        p = pages.get(pid)
        if not p:
            from errors import NotFoundError
            raise NotFoundError(f"not found: {pid}", code="page_not_found")
        return {"id": pid, "title": p["title"], "body": {"storage": {"value": p.get("body_html", "")}},
                "space": {"key": p.get("space", "AI")}, "version": {"number": 1}, "type": "page"}
    fake.get_page.side_effect = get_page
    def get_children(pid, limit=50):
        return [{"id": cid, "title": pages[cid]["title"]} for cid in pages.get(pid, {}).get("children", [])]
    fake.get_children.side_effect = get_children
    monkeypatch.setattr(cf_client, "_test_client", fake)
    return fake


def test_reingest_same_source_id_no_duplicate(monkeypatch, tmp_path, capsys):
    v = _vault(monkeypatch, tmp_path)
    vault.resolve_vault(path=v, skill_root=tmp_path / "skill")
    _mock_cf(monkeypatch, **{"42": {"title": "Same Page", "body_html": "<p>content</p>"}})
    enrich.set_provider(FakeEnrichProvider())
    try:
        run.main(["confluence", "ingest", "42", "--yes", "--json"])
        capsys.readouterr()
        run.main(["confluence", "ingest", "42", "--yes", "--json"])
    finally:
        enrich.set_provider(None)
    files = list((v / "confluence").rglob("*.md"))
    assert len(files) == 1, f"expected 1, got {[f.name for f in files]}"


def test_nested_tree_creates_subdirs(monkeypatch, tmp_path, capsys):
    """Confluence tree with depth creates nested directories mirroring hierarchy."""
    v = _vault(monkeypatch, tmp_path)
    vault.resolve_vault(path=v, skill_root=tmp_path / "skill")
    _mock_cf(monkeypatch, **{
        "100": {"title": "Root", "body_html": "<p>r</p>", "children": ["101", "102"]},
        "101": {"title": "Child A", "body_html": "<p>a</p>", "children": ["103"]},
        "102": {"title": "Child B", "body_html": "<p>b</p>"},
        "103": {"title": "Grandchild", "body_html": "<p>g</p>"},
    })
    enrich.set_provider(FakeEnrichProvider())
    try:
        rc = run.main(["confluence", "ingest", "100", "--depth", "2", "--yes", "--json"])
        assert rc == 0
    finally:
        enrich.set_provider(None)
    payload = json.loads(capsys.readouterr().out)
    assert payload["data"]["count"] == 4
    # Root at top level
    assert (v / "confluence" / "root.md").exists()
    # Children in root/ subdir
    assert (v / "confluence" / "root" / "child-a.md").exists()
    assert (v / "confluence" / "root" / "child-b.md").exists()
    # Grandchild in root/child-a/ subdir
    assert (v / "confluence" / "root" / "child-a" / "grandchild.md").exists()


def test_tags_llm_only_no_mechanical(monkeypatch, tmp_path, capsys):
    """Without LLM (stub), tags are empty — no mechanical noise."""
    v = _vault(monkeypatch, tmp_path)
    vault.resolve_vault(path=v, skill_root=tmp_path / "skill")
    enrich.set_provider(None)  # stub
    run.main(["note", "add", "hello", "--title", "T", "--yes", "--json"])
    capsys.readouterr()
    files = list((v / "note").glob("*.md"))
    meta, _ = fm_parse(files[0].read_text(encoding="utf-8"))
    assert meta.get("tags", []) == []  # no mechanical tags


def test_cross_links_use_real_paths():
    from okf.concept import Concept
    enrich.set_provider(FakeEnrichProvider())
    try:
        c = Concept(type="Note", title="New", body="about Existing")
        enrich.enrich(c, {"Existing": "note/existing.md"})
        assert "/path/to/" not in (c.body or "")
        assert "/note/existing.md" in (c.body or "")
    finally:
        enrich.set_provider(None)
