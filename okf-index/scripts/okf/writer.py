"""Write an OKF concept into the vault: deterministic slug, uniqueness, log append."""
from __future__ import annotations

import datetime as _dt
from pathlib import Path

from okf import frontmatter
from okf.concept import Concept, make_source_id
from okf.log import append_log
from okf.slug import slugify, unique_slug


def _today() -> str:
    return _dt.date.today().isoformat()


def write_concept(vault: Path, concept: Concept) -> Path:
    vault = Path(vault)
    source = concept.source or "misc"
    source_dir = vault / source
    source_dir.mkdir(parents=True, exist_ok=True)
    taken = {p.stem for p in source_dir.glob("*.md")}
    base = slugify(concept.title or "untitled")
    stem = unique_slug(base, taken)
    path = source_dir / f"{stem}.md"
    if not concept.source_id:
        concept.source_id = make_source_id(source, concept.body)
    text = frontmatter.dump(concept.frontmatter(), concept.body)
    path.write_text(text, encoding="utf-8")
    append_log(vault / "log.md", _today(), [f"**Ingest**: {source}/{stem}"])
    return path


def list_titles(vault: Path) -> list[str]:
    """Return titles of all existing concepts in the vault (no DB needed)."""
    titles: list[str] = []
    for path in sorted(vault.rglob("*.md")):
        if path.name in ("index.md", "log.md"):
            continue
        meta, _body = frontmatter.parse(path.read_text(encoding="utf-8"))
        if meta and meta.get("title"):
            titles.append(meta["title"])
    return titles
