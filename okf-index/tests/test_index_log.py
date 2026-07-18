"""SCIU 8 tests: index.md + log.md generators."""
from okf import index as idx
from okf import log


def test_index_no_frontmatter_except_root_okf_version():
    items = [{"title": "A", "description": "d", "rel": "a.md", "type": "Note"}]
    assert "---" not in idx.generate_index(items)
    root = idx.generate_index(items, okf_version="0.1")
    assert 'okf_version: "0.1"' in root


def test_index_sections_carry_descriptions():
    items = [{"title": "A", "description": "важно", "rel": "a.md", "type": "Note"}]
    out = idx.generate_index(items)
    assert "## Note" in out
    assert "важно" in out
    assert "[A](a.md)" in out


def test_log_iso_date_newest_first():
    out = log.format_log({"2026-07-01": ["old"], "2026-07-18": ["new"]})
    assert out.index("## 2026-07-18") < out.index("## 2026-07-01")


def test_log_entries_append(tmp_path):
    p = tmp_path / "log.md"
    log.append_log(p, "2026-07-18", ["**Update**: x"])
    log.append_log(p, "2026-07-18", ["**Creation**: y"])
    log.append_log(p, "2026-07-10", ["**Init**: z"])
    text = p.read_text(encoding="utf-8")
    assert "**Update**: x" in text
    assert "**Creation**: y" in text
    assert "**Init**: z" in text
    # newest first
    assert text.index("## 2026-07-18") < text.index("## 2026-07-10")
