"""SCIU - Task 3 tests: Confluence connector (mocked HTTP)."""
import json
from unittest.mock import MagicMock

import confluence.client as client
import enrich
import run
import vault
from enricher import FakeEnrichProvider
from okf.frontmatter import parse as fm_parse


def _mock_client(monkeypatch, **pages):
    """pages: {page_id: {title, body_html, space}}"""
    from confluence.client import ConfluenceClient

    fake = MagicMock(spec=ConfluenceClient)
    fake.base = "https://c.example.com"

    def get_page(pid):
        p = pages.get(pid)
        if not p:
            from errors import NotFoundError
            raise NotFoundError(f"page not found: {pid}", code="page_not_found")
        return {
            "id": pid,
            "title": p["title"],
            "body": {"storage": {"value": p.get("body_html", "")}},
            "space": {"key": p.get("space", "TEST")},
            "version": {"number": 1},
            "type": "page",
        }

    fake.get_page.side_effect = get_page

    def search(cql, limit=20):
        q = cql.replace("text ~ '", "").split("'")[0]
        results = []
        for pid, p in pages.items():
            if q.lower() in p["title"].lower():
                results.append({"content": {"id": pid}, "title": p["title"], "url": f"/spaces/{p.get('space','TEST')}/pages/{pid}"})
        return results[:limit]

    fake.search.side_effect = search
    monkeypatch.setattr(client, "_test_client", fake)
    return fake


def _vault(monkeypatch, tmp_path):
    v = tmp_path / "vault"
    monkeypatch.setenv("OKF_VAULT_PATH", str(v))
    return v


def test_confluence_get_page_mock(monkeypatch, capsys):
    _mock_client(monkeypatch, **{"123": {"title": "Test Page", "body_html": "<h1>Hello</h1><p>world</p>", "space": "DEMO"}})
    rc = run.main(["confluence", "get", "123", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["data"]["title"] == "Test Page"
    assert "Hello" in payload["data"]["body"]


def test_confluence_get_not_found(monkeypatch):
    _mock_client(monkeypatch)
    rc = run.main(["confluence", "get", "999", "--json"])
    assert rc == 3


def test_confluence_search_mock(monkeypatch, capsys):
    _mock_client(monkeypatch, **{"1": {"title": "Page One"}, "2": {"title": "Page Two"}})
    rc = run.main(["confluence", "search", "One", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["data"]["count"] == 1


def test_confluence_ingest_writes_okf(monkeypatch, tmp_path, capsys):
    v = _vault(monkeypatch, tmp_path)
    vault.resolve_vault(path=v, skill_root=tmp_path / "skill")
    _mock_client(monkeypatch, **{"42": {"title": "CF Page", "body_html": "<p>confluence content</p>"}})
    enrich.set_provider(FakeEnrichProvider())
    try:
        rc = run.main(["confluence", "ingest", "42", "--yes", "--json"])
        assert rc == 0
    finally:
        enrich.set_provider(None)
    payload = json.loads(capsys.readouterr().out)
    rel = payload["data"]["created"]["path"]
    meta, body = fm_parse((v / rel).read_text(encoding="utf-8"))
    assert meta["type"] == "ConfluencePage"
    assert meta["title"] == "CF Page"
    assert meta["source"] == "confluence"
