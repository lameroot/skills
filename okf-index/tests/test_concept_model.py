"""SCIU 7 tests: OKF concept model (frontmatter round-trip, slug, source_id, producer keys)."""
import pytest

from okf import frontmatter, slug
from okf.concept import Concept, make_source_id


def test_frontmatter_roundtrip_preserves_cyrillic_and_colons():
    meta = {"type": "Note", "title": "Привет: мир", "tags": ["раз", "two"]}
    body = "тело с Cyrillic и : двоеточиями"
    text = frontmatter.dump(meta, body)
    m, b = frontmatter.parse(text)
    assert m["type"] == "Note"
    assert m["title"] == "Привет: мир"
    assert m["tags"] == ["раз", "two"]
    assert "тело" in b


def test_type_required_nonempty():
    c = Concept(type="", title="x")
    with pytest.raises(ValueError):
        c.frontmatter()


def test_slug_pure_cyrillic_falls_back_deterministically():
    s1 = slug.slugify("Привет мир")
    s2 = slug.slugify("Привет мир")
    assert s1 == s2
    assert s1 and s1.isascii()
    assert s1 == "privet-mir"


def test_slug_mixed_keeps_ascii():
    assert slug.slugify("API Reference 2") == "api-reference-2"


def test_slug_collision_suffixes():
    assert slug.unique_slug("foo", {"foo"}) == "foo-2"
    assert slug.unique_slug("foo", {"foo", "foo-2"}) == "foo-3"
    assert slug.unique_slug("foo", set()) == "foo"


def test_source_id_stable_across_path_move():
    a = make_source_id("doc", "same body content")
    b = make_source_id("doc", "same body content")
    assert a == b
    assert a.startswith("doc-")


def test_producer_keys_emitted():
    c = Concept(type="Document", title="T", body="B", source="doc")
    c.source_id = make_source_id("doc", "B")
    fm = c.frontmatter()
    for k in ("type", "source", "source_id", "content_hash", "okf_version"):
        assert k in fm
    assert fm["okf_version"] == "0.1"
