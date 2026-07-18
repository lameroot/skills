"""SCIU - Task 6 tests: Telegram connector (mocked messages)."""
import json

import enrich
import run
import telegram as tg
import vault
from enricher import FakeEnrichProvider
from okf.frontmatter import parse as fm_parse


def _vault(monkeypatch, tmp_path):
    v = tmp_path / "vault"
    monkeypatch.setenv("OKF_VAULT_PATH", str(v))
    return v


def test_telegram_ingest_mock(monkeypatch, tmp_path, capsys):
    v = _vault(monkeypatch, tmp_path)
    vault.resolve_vault(path=v, skill_root=tmp_path / "skill")
    tg._test_messages = [{"id": 1, "text": "Hello from TG", "date": "2026-07-18T00:00:00Z"}]
    enrich.set_provider(FakeEnrichProvider())
    try:
        rc = run.main(["telegram", "ingest", "testchan", "--yes", "--json"])
        assert rc == 0
    finally:
        tg._test_messages = None
        enrich.set_provider(None)
    payload = json.loads(capsys.readouterr().out)
    assert payload["data"]["count"] == 1
    meta, _ = fm_parse(list((v / "telegram").rglob("*.md"))[0].read_text())
    assert meta["type"] == "TelegramMessage"


def test_telegram_dry_run(monkeypatch, tmp_path, capsys):
    tg._test_messages = [{"id": 1, "text": "hi", "date": ""}]
    try:
        rc = run.main(["telegram", "ingest", "tc", "--dry-run", "--json"])
        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["data"]["dry_run"] is True
    finally:
        tg._test_messages = None
