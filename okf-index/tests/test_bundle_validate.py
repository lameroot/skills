"""SCIU 9 tests: bundle validate (SPEC §9 conformance)."""
import json

import run
from okf.validate import validate_bundle


def _write(p, text):
    from pathlib import Path

    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def test_concept_without_type_rejected(tmp_path):
    _write(tmp_path / "a.md", "---\ntitle: A\n---\nbody")
    r = validate_bundle(tmp_path)
    assert not r["conformant"]
    assert any(v["rule"] == "type" for v in r["violations"])


def test_unparseable_frontmatter_reported_not_raised(tmp_path):
    _write(tmp_path / "b.md", "no frontmatter at all")
    r = validate_bundle(tmp_path)  # must not raise
    assert not r["conformant"]
    assert any(v["rule"] == "frontmatter" for v in r["violations"])


def test_reserved_filenames_exempt(tmp_path):
    _write(tmp_path / "index.md", "# Index no frontmatter")
    _write(tmp_path / "log.md", "# Log")
    _write(tmp_path / "note.md", "---\ntype: Note\n---\nbody")
    r = validate_bundle(tmp_path)
    assert r["conformant"], r["violations"]


def test_conformant_passes(tmp_path):
    _write(tmp_path / "note.md", "---\ntype: Note\ntitle: A\n---\nbody")
    r = validate_bundle(tmp_path)
    assert r["conformant"]


def test_collects_all_errors(tmp_path):
    _write(tmp_path / "a.md", "---\ntitle: A\n---\n")  # no type
    _write(tmp_path / "b.md", "garbage")  # no frontmatter
    r = validate_bundle(tmp_path)
    assert len(r["violations"]) == 2


def test_bundle_validate_cli_exit_codes(tmp_path, capsys):
    _write(tmp_path / "note.md", "---\ntype: Note\n---\nbody")
    rc = run.main(["bundle", "validate", "--bundle", str(tmp_path), "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["data"]["conformant"] is True

    _write(tmp_path / "bad.md", "no frontmatter")
    rc = run.main(["bundle", "validate", "--bundle", str(tmp_path), "--json"])
    assert rc == 1
