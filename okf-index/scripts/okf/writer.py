"""Write an OKF concept into the vault: source_id dedup, slug, log append."""
from __future__ import annotations

import datetime as _dt
from pathlib import Path

from okf import frontmatter
from okf.concept import Concept, make_source_id
from okf.log import append_log
from okf.slug import slugify, unique_slug


def _today() -> str:
    return _dt.date.today().isoformat()


def _find_by_source_id(source_dir: Path, source_id: str) -> Path | None:
    """Find an existing concept file by source_id (for update-in-place)."""
    if not source_id or not source_dir.exists():
        return None
    for p in source_dir.glob("*.md"):
        try:
            meta, _ = frontmatter.parse(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if meta.get("source_id") == source_id:
            return p
    return None


def write_concept(vault: Path, concept: Concept) -> Path:
    vault = Path(vault)
    source = concept.source or "misc"
    source_dir = vault / source

    if not concept.source_id:
        concept.source_id = make_source_id(source, concept.body)

    # Dedup by source_id: update existing file instead of creating -2/-3 duplicate
    existing = _find_by_source_id(source_dir, concept.source_id)
    if existing:
        path = existing
    else:
        source_dir.mkdir(parents=True, exist_ok=True)
        taken = {p.stem for p in source_dir.glob("*.md")}
        base = slugify(concept.title or "untitled")
        stem = unique_slug(base, taken)
        path = source_dir / f"{stem}.md"

    text = frontmatter.dump(concept.frontmatter(), concept.body)
    path.write_text(text, encoding="utf-8")
    append_log(vault / "log.md", _today(), [f"**Ingest**: {source}/{path.stem}"])
    return path


def list_titles(vault: Path) -> list[str]:
    """Return titles of all existing concepts (legacy — for enrich prompt context)."""
    return list(list_concepts(vault).keys())


def list_concepts(vault: Path) -> dict[str, str]:
    """Return {title: relative_path} for all concepts (for cross-link resolution)."""
    vault = Path(vault)
    result: dict[str, str] = {}
    if not vault.exists():
        return result
    for path in sorted(vault.rglob("*.md")):
        if path.name in ("index.md", "log.md"):
            continue
        try:
            meta, _ = frontmatter.parse(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        title = meta.get("title", "")
        if title:
            result[title] = str(path.relative_to(vault))
    return result
