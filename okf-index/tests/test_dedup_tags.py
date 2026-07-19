"""Tests: source_id dedup (no duplicates on re-ingest) + mechanical tags."""
import json

import enrich
import run
import vault
from enricher import FakeEnrichProvider
from okf.frontmatter import parse as fm_parse


def _vault(monkeypatch, tmp_path):
    v = tmp_path / "vault"
    monkeypatch.setenv("OKF_VAULT_PATH", str(v))
    return v


def test_reingest_same_source_id_no_duplicate(monkeypatch, tmp_path, capsys):
    """Ingesting the same Confluence page twice should update, not create -2."""
    v = _vault(monkeypatch, tmp_path)
    vault.resolve_vault(path=v, skill_root=tmp_path / "skill")
    # Mock confluence client
    from unittest.mock import MagicMock
    import confluence.client as cf_client
    from confluence.client import ConfluenceClient
    fake = MagicMock(spec=ConfluenceClient)
    fake.base = "https://c.example.com"
    fake.get_page.return_value = {
        "id": "42", "title": "Same Page", "body": {"storage": {"value": "<p>content</p>"}},
        "space": {"key": "AI"}, "version": {"number": 1}, "type": "page",
    }
    monkeypatch.setattr(cf_client, "_test_client", fake)
    enrich.set_provider(FakeEnrichProvider())
    try:
        # First ingest
        run.main(["confluence", "ingest", "42", "--yes", "--json"])
        capsys.readouterr()
        # Second ingest (same page)
        run.main(["confluence", "ingest", "42", "--yes", "json"] if False else ["confluence", "ingest", "42", "--yes", "--json"])
        payload = json.loads(capsys.readouterr().out)
    finally:
        enrich.set_provider(None)
    # Only ONE file in confluence/ — no -2 suffix
    files = list((v / "confluence").glob("*.md"))
    assert len(files) == 1, f"expected 1 file, got {[f.name for f in files]}"
    assert "-2" not in files[0].stem


def test_mechanical_tags_confluence(monkeypatch, tmp_path, capsys):
    """Confluence concepts get space key as a mechanical tag."""
    v = _vault(monkeypatch, tmp_path)
    vault.resolve_vault(path=v, skill_root=tmp_path / "skill")
    from unittest.mock import MagicMock
    import confluence.client as cf_client
    from confluence.client import ConfluenceClient
    fake = MagicMock(spec=ConfluenceClient)
    fake.base = "https://c.example.com"
    fake.get_page.return_value = {
        "id": "99", "title": "Tagged", "body": {"storage": {"value": "<p>x</p>"}},
        "space": {"key": "DEV"}, "version": {"number": 1}, "type": "page",
    }
    monkeypatch.setattr(cf_client, "_test_client", fake)
    enrich.set_provider(None)  # stub mode — no LLM tags
    run.main(["confluence", "ingest", "99", "--yes", "--json"])
    capsys.readouterr()
    files = list((v / "confluence").glob("*.md"))
    meta, _ = fm_parse(files[0].read_text(encoding="utf-8"))
    assert "dev" in meta.get("tags", []), f"expected 'dev' tag, got {meta.get('tags')}"


def test_mechanical_tags_note(monkeypatch, tmp_path, capsys):
    """Notes get 'note' tag even in stub mode."""
    v = _vault(monkeypatch, tmp_path)
    vault.resolve_vault(path=v, skill_root=tmp_path / "skill")
    enrich.set_provider(None)
    run.main(["note", "add", "hello", "--title", "T", "--yes", "--json"])
    capsys.readouterr()
    files = list((v / "note").glob("*.md"))
    meta, _ = fm_parse(files[0].read_text(encoding="utf-8"))
    assert "note" in meta.get("tags", [])


def test_cross_links_use_real_paths(monkeypatch, tmp_path, capsys):
    """Cross-links should use actual concept paths, not /path/to/ placeholders."""
    from okf.concept import Concept
    import enrich as enrich_mod
    enrich_mod.set_provider(FakeEnrichProvider())
    try:
        c = Concept(type="Note", title="New", body="about Existing")
        enrich_mod.enrich(c, {"Existing": "note/existing.md"})
        assert "/path/to/" not in (c.body or "")
        assert "/note/existing.md" in (c.body or "")
    finally:
        enrich_mod.set_provider(None)
