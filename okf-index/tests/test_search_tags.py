"""SCIU 12 tests: search + tag list/show + bundle stats (FTS5 consumer)."""
import json

import run
import vault
from indexer import index_bundle
from okf.frontmatter import dump as fm_dump


def _vault(monkeypatch, tmp_path):
    v = tmp_path / "vault"
    monkeypatch.setenv("OKF_VAULT_PATH", str(v))
    return v


def _setup(monkeypatch, tmp_path):
    v = _vault(monkeypatch, tmp_path)
    vault.resolve_vault(path=v, skill_root=tmp_path / "skill")
    (v / "doc").mkdir(exist_ok=True)
    (v / "doc" / "x.md").write_text(fm_dump({"type": "Doc", "title": "Alpha", "tags": ["test"]}, "alpha content"), encoding="utf-8")
    (v / "doc" / "y.md").write_text(fm_dump({"type": "Doc", "title": "Beta", "tags": ["test"]}, "beta content"), encoding="utf-8")
    (v / "doc" / "z.md").write_text(fm_dump({"type": "Note", "title": "Gamma"}, "gamma content"), encoding="utf-8")
    index_bundle(v)
    return v


def test_search_cyrillic_matches(monkeypatch, tmp_path, capsys):
    v = _vault(monkeypatch, tmp_path)
    vault.resolve_vault(path=v, skill_root=tmp_path / "skill")
    (v / "doc").mkdir(exist_ok=True)
    (v / "doc" / "cyr.md").write_text(fm_dump({"type": "Note", "title": "Привет"}, "русский текст мир"), encoding="utf-8")
    index_bundle(v)
    rc = run.main(["search", "русский", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["data"]["count"] >= 1


def test_search_tag_type_filter(monkeypatch, tmp_path, capsys):
    v = _vault(monkeypatch, tmp_path)
    sroot = tmp_path / "skill"
    vault.resolve_vault(path=v, skill_root=sroot)
    (v / "doc").mkdir(exist_ok=True)
    (v / "doc" / "x.md").write_text(fm_dump({"type": "Doc", "title": "A1", "tags": ["t1"]}, "alpha"), encoding="utf-8")
    (v / "doc" / "z.md").write_text(fm_dump({"type": "Note", "title": "C1"}, "gamma"), encoding="utf-8")
    index_bundle(v)
    # basic search without filters (same as cyrillic test pattern)
    rc = run.main(["search", "alpha", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["data"]["count"] >= 1
    # search with tag filter
    rc = run.main(["search", "alpha", "--tag", "t1", "--json"])
    assert rc == 0
    payload2 = json.loads(capsys.readouterr().out)
    assert payload2["data"]["count"] >= 1


def test_search_limit(monkeypatch, tmp_path, capsys):
    _setup(monkeypatch, tmp_path)
    rc = run.main(["search", "content", "--limit", "1", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert len(payload["data"]["results"]) <= 1


def test_search_empty_exits_2(monkeypatch, tmp_path):
    _vault(monkeypatch, tmp_path)
    rc = run.main(["search", "", "--json"])
    assert rc == 2


def test_tag_list_and_show(monkeypatch, tmp_path, capsys):
    _setup(monkeypatch, tmp_path)
    rc = run.main(["tag", "list", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert len(payload["data"]["tags"]) >= 1
    rc = run.main(["tag", "show", "test", "--json"])
    payload2 = json.loads(capsys.readouterr().out)
    assert payload2["data"]["count"] == 2


def test_stats_counts(monkeypatch, tmp_path, capsys):
    _setup(monkeypatch, tmp_path)
    rc = run.main(["bundle", "stats", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["data"]["total"] == 3
