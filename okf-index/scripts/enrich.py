"""Enrichment orchestrator. Mechanical tags (always) + LLM (if configured) + cross-links."""
from __future__ import annotations

from enricher import EnrichProvider, EnrichResult, create_provider
from okf.concept import Concept

_provider: EnrichProvider | None | bool = None  # None=uninitialized, False=stub, instance=provider


def _first(text: str) -> str:
    for line in (text or "").splitlines():
        s = line.strip()
        if s:
            return s.lstrip("#").strip()
    return ""


first_line = _first  # public alias used by connectors/note.py


def _get_provider() -> EnrichProvider | None:
    global _provider
    if _provider is None:
        _provider = create_provider() or False
    return _provider if _provider else None  # type: ignore[return-value]


def set_provider(p: EnrichProvider | None) -> None:
    global _provider
    _provider = p


def enrich(
    concept: Concept,
    title_to_path: dict[str, str] | None = None,
) -> Concept:
    """Always-on enrichment: LLM description + tags + cross-links (stub fallback)."""
    existing_titles = list(title_to_path.keys()) if title_to_path else []

    # LLM enrichment — if configured
    prov = _get_provider()
    result: EnrichResult | None = None
    if prov:
        try:
            result = prov.enrich(concept, existing_titles)
        except Exception:
            result = None

    # Description
    if result and result.description:
        concept.description = result.description
    else:
        concept.description = f"[stub] {_first(concept.body)}"

    # Tags: LLM only (no mechanical tags — user wants meaningful search tags)
    if result and result.tags:
        concept.tags = list(dict.fromkeys(result.tags))  # dedup, preserve order

    # Cross-links: map LLM-suggested titles to real concept paths
    if result and result.suggested_links and title_to_path:
        links = []
        for title in result.suggested_links:
            rel = title_to_path.get(title)
            if rel:
                links.append(f"* [{title}](/{rel})")
        if links:
            concept.body = (concept.body or "").rstrip() + "\n\n## See also\n\n" + "\n".join(links)

    return concept
