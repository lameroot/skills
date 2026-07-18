"""SCIU - Task 4 tests: web connector (mocked crawl4ai)."""
import json

import enrich
import run
import vault
import web
from enricher import FakeEnrichProvider


def _vault(monkeypatch, tmp_path):
    v = tmp_path / "vault"
    monkeypatch.setenv("OKF_VAULT_PATH", str(v))
    return v


def test_web_fetch_writes_okf(monkeypatch, tmp_path, capsys):
    v = _vault(monkeypatch, tmp_path)
    vault.resolve_vault(path=v, skill_root=tmp_path / "skill")
    web._results_override = [("https://x.com/page", "# Hello\nworld", "Hello")]
    enrich.set_provider(FakeEnrichProvider())
    try:
        rc = run.main(["web", "fetch", "https://x.com/page", "--yes", "--json"])
        assert rc == 0
    finally:
        web._results_override = None
        enrich.set_provider(None)
    payload = json.loads(capsys.readouterr().out)
    assert payload["data"]["created"]["type"] == "WebPage"


def test_web_fetch_dry_run_noop(monkeypatch, tmp_path, capsys):
    _vault(monkeypatch, tmp_path)
    web._results_override = [("https://x.com/x", "md", "T")]
    try:
        rc = run.main(["web", "fetch", "https://x.com/x", "--dry-run", "--json"])
        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["data"]["dry_run"] is True
    finally:
        web._results_override = None


def test_web_crawl_batch(monkeypatch, tmp_path, capsys):
    v = _vault(monkeypatch, tmp_path)
    vault.resolve_vault(path=v, skill_root=tmp_path / "skill")
    web._results_override = [
        ("https://x.com/a", "# A", "A"),
        ("https://x.com/b", "# B", "B"),
    ]
    enrich.set_provider(FakeEnrichProvider())
    try:
        rc = run.main(["web", "crawl", "https://x.com", "--max-depth", "1", "--max-pages", "5", "--yes", "--json"])
        assert rc == 0
    finally:
        web._results_override = None
        enrich.set_provider(None)
    payload = json.loads(capsys.readouterr().out)
    assert payload["data"]["count"] == 2
