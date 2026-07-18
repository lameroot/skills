"""SCIU 10 tests: note/doc connectors + enrich stub + vault safety."""
import json
from pathlib import Path

import pytest

import run
import vault
from connectors import doc
from errors import UsageError
from okf.validate import validate_bundle


def _vault(monkeypatch, tmp_path):
    v = tmp_path / "vault"
    monkeypatch.setenv("OKF_VAULT_PATH", str(v))
    return v


def test_note_add_writes_conformant_concept(monkeypatch, tmp_path):
    v = _vault(monkeypatch, tmp_path)
    rc = run.main(["note", "add", "# Привет\nмир", "--title", "Привет", "--yes", "--json"])
    assert rc == 0
    assert (v / "note").is_dir()
    assert validate_bundle(v)["conformant"]
    # concept file has frontmatter + type
    md = next((v / "note").glob("*.md"))
    text = md.read_text(encoding="utf-8")
    assert "type: Note" in text
    assert "Привет" in text


def test_empty_note_exits_2(monkeypatch, tmp_path):
    _vault(monkeypatch, tmp_path)
    rc = run.main(["note", "add", "   ", "--yes", "--json"])
    assert rc == 2


def test_doc_ingest_md_txt_recursive_pdf_skipped(monkeypatch, tmp_path, capsys):
    v = _vault(monkeypatch, tmp_path)
    src = tmp_path / "src"
    sub = src / "sub"
    sub.mkdir(parents=True)
    (src / "a.md").write_text("alpha", encoding="utf-8")
    (sub / "b.txt").write_text("beta", encoding="utf-8")
    (src / "c.pdf").write_text("%PDF-", encoding="utf-8")
    (src / "d.exe").write_text("binary", encoding="utf-8")
    monkeypatch.setattr(doc, "_convert_office", lambda p: f"[converted {p.name}]")
    rc = run.main(["doc", "ingest", str(src), "--recursive", "--yes", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)["data"]
    assert len(payload["created"]) == 3  # a.md + b.txt + c.pdf
    assert "d.exe" in payload["skipped"]
    assert validate_bundle(v)["conformant"]


def test_dry_run_no_write_then_yes_and_autoconfirm(monkeypatch, tmp_path, capsys):
    v = _vault(monkeypatch, tmp_path)
    # dry-run: no write (vault not created)
    rc = run.main(["note", "add", "hello", "--dry-run", "--json"])
    assert rc == 0
    assert not v.exists()
    # --yes writes
    rc = run.main(["note", "add", "hello", "--yes", "--json"])
    assert rc == 0
    assert (v / "note").is_dir()
    assert list((v / "note").glob("*.md"))
    # AUTO_CONFIRM
    monkeypatch.setenv("OKF_INDEX_AUTO_CONFIRM", "1")
    rc = run.main(["note", "add", "second note", "--json"])
    assert rc == 0


def test_enrich_stub_description_first_line():
    from enrich import enrich, first_line
    from okf.concept import Concept

    assert first_line("# Заголовок\nrest") == "Заголовок"
    c = Concept(type="Note", title="T", body="# Привет\nтело")
    enrich(c)
    assert "[stub]" in c.description and "Привет" in c.description


def test_vault_in_skill_dir_rejected(monkeypatch, tmp_path):
    skill_root = tmp_path / "skill"
    skill_root.mkdir()
    inside = skill_root / "vault"
    with pytest.raises(UsageError):
        vault.resolve_vault(path=inside, skill_root=skill_root)


def test_vault_writes_gitignore(monkeypatch, tmp_path):
    v = vault.resolve_vault(path=tmp_path / "okfvault", skill_root=tmp_path / "skill")
    assert (v / ".gitignore").read_text().count(".okf/") >= 1
