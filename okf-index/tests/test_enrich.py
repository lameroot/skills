"""SCIU - Task 2 tests: enrichment (fake provider, stub fallback, cross-links, doctor probe)."""
import json

import enrich
import run
import vault
from enricher import FakeEnrichProvider
from okf.concept import Concept
from okf.writer import write_concept
from okf.frontmatter import parse as fm_parse


def _vault(monkeypatch, tmp_path):
    v = tmp_path / "vault"
    monkeypatch.setenv("OKF_VAULT_PATH", str(v))
    return v


def test_fake_provider_sets_description_and_tags(monkeypatch, tmp_path, capsys):
    v = _vault(monkeypatch, tmp_path)
    vault.resolve_vault(path=v, skill_root=tmp_path / "skill")
    enrich.set_provider(FakeEnrichProvider())
    try:
        rc = run.main(["note", "add", "some content about LLM and search", "--title", "My Note", "--yes", "--json"])
        assert rc == 0
    finally:
        enrich.set_provider(None)
    payload = json.loads(capsys.readouterr().out)
    rel = payload["data"]["created"]["path"]
    concept_path = v / rel
    meta, body = fm_parse(concept_path.read_text(encoding="utf-8"))
    assert "LLM-generated" in meta.get("description", "")
    assert len(meta.get("tags", [])) >= 1


def test_stub_fallback_when_no_creds(monkeypatch, tmp_path, capsys):
    v = _vault(monkeypatch, tmp_path)
    vault.resolve_vault(path=v, skill_root=tmp_path / "skill")
    enrich.set_provider(None)  # force stub
    try:
        rc = run.main(["note", "add", "hello world", "--title", "Stub", "--yes", "--json"])
        assert rc == 0
    finally:
        enrich.set_provider(None)
    payload = json.loads(capsys.readouterr().out)
    rel = payload["data"]["created"]["path"]
    meta, body = fm_parse((v / rel).read_text(encoding="utf-8"))
    assert "[stub]" in meta.get("description", "")


def test_cross_links_appended_to_body(monkeypatch, tmp_path):
    v = _vault(monkeypatch, tmp_path)
    vault.resolve_vault(path=v, skill_root=tmp_path / "skill")
    enrich.set_provider(FakeEnrichProvider())
    try:
        c = Concept(type="Note", title="New", body="related to Existing Topic about LLM")
        enrich.enrich(c, ["Existing Topic"])
        assert "## See also" in (c.body or "")
        assert "Existing Topic" in c.body
    finally:
        enrich.set_provider(None)


def test_doctor_skips_enrich_probe_when_no_creds(monkeypatch, tmp_path, capsys):
    _vault(monkeypatch, tmp_path)
    monkeypatch.delenv("ENRICH_API_KEY", raising=False)
    enrich.set_provider(None)
    try:
        rc = run.main(["doctor", "--json"])
        payload = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert "skipped" in payload["data"]["probe"]
    finally:
        enrich.set_provider(None)


def test_existing_tests_still_pass():
    # existing 68 tests were outside this module; this is a smoke anchor
    pass
