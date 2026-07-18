"""SCIU - Task 7+8 tests: viz.html + sources.yaml build."""
import json

import run
import vault


def _vault(monkeypatch, tmp_path):
    v = tmp_path / "vault"
    monkeypatch.setenv("OKF_VAULT_PATH", str(v))
    return v


def test_viz_generates_html(monkeypatch, tmp_path, capsys):
    v = _vault(monkeypatch, tmp_path)
    vault.resolve_vault(path=v, skill_root=tmp_path / "skill")
    (v / "doc").mkdir(exist_ok=True)
    (v / "doc" / "a.md").write_text("---\ntype: Doc\ntitle: A\n---\nbody [link](/doc/b.md)", encoding="utf-8")
    (v / "doc" / "b.md").write_text("---\ntype: Doc\ntitle: B\n---\nbody", encoding="utf-8")
    from indexer import index_bundle
    index_bundle(v)
    rc = run.main(["bundle", "visualize", "--out", str(v / "viz.html"), "--json"])
    assert rc == 0
    html = (v / "viz.html").read_text(encoding="utf-8")
    assert "<html" in html and "cytoscape" in html


def test_sources_build_dry_run(monkeypatch, tmp_path, capsys):
    v = _vault(monkeypatch, tmp_path)
    vault.resolve_vault(path=v, skill_root=tmp_path / "skill")
    manifest = tmp_path / "sources.yaml"
    manifest.write_text("sources:\n  note:\n    - text: hello\n      title: Test\n", encoding="utf-8")
    rc = run.main(["bundle", "build", "--from", str(manifest), "--dry-run", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["data"]["dry_run"] is True


def test_sources_build_yes(monkeypatch, tmp_path, capsys):
    v = _vault(monkeypatch, tmp_path)
    vault.resolve_vault(path=v, skill_root=tmp_path / "skill")
    manifest = tmp_path / "sources.yaml"
    manifest.write_text("sources:\n  note:\n    - text: hello from manifest\n      title: Manifest Note\n", encoding="utf-8")
    rc = run.main(["bundle", "build", "--from", str(manifest), "--yes", "--json"])
    assert rc == 0
    assert (v / "note").is_dir()
